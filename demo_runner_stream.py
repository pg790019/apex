"""
Demo runner.

Skips the real Jira webhook and invokes the orchestrator directly for a
given ticket ID. This version is interrupt-aware AND streaming-aware:
it streams coordinator and subagent output live as the graph runs, and
whenever the graph pauses (either the automatic task-call approval
checkpoints, or an explicit request_human_review escalation), it prints
what's pending and asks you for a decision on the terminal, then resumes
the same run via streaming.

Usage:
    python demo_runner.py PROJ-123

Requires a real Jira ticket to exist at that key -- create one throwaway
ticket in a sandbox/test project before the demo.
"""

import sys

from langgraph.types import Command

import config
from orchestrator import build_orchestrator, _build_checkpointer
from workspace import resolve_workspace_dir_name
from logging_setup import get_logger

logger = get_logger(__name__)


def _stream_run(agent, stream_input, run_config):
    """Run one leg of the graph, streaming coordinator + subagent output live.

    Returns the drained stream object so the caller can inspect
    `.interrupted`, `.interrupts`, and `.output`.
    """
    stream = agent.stream_events(stream_input, config=run_config, version="v3")

    for name, item in stream.interleave("messages", "subagents"):
        if name == "messages":
            if item.text:
                print("--- [coordinator] ---")
                print(item.text)
                print()
        else:
            print(f"--- [subagent: {item.name}] started (status={item.status}) ---")
            for message in item.messages:
                if message.text:
                    print(f"--- [{item.name}] ---")
                    print(message.text)
                    print()
            print(f"--- [subagent: {item.name}] status: {item.status} ---")

    return stream


def _handle_task_approval(interrupt_value: dict) -> list:
    """Ask the user to approve/reject each pending subagent (task) call.

    Returns the decisions list, in the same order as action_requests, in the
    shape agent.stream_events(Command(resume={"decisions": [...]})) expects.
    """
    action_requests = interrupt_value["action_requests"]
    review_configs = interrupt_value["review_configs"]
    config_map = {cfg["action_name"]: cfg for cfg in review_configs}

    print("\n=== HUMAN APPROVAL REQUIRED: subagent launch ===")
    decisions = []
    for action in action_requests:
        review_config = config_map.get(action["name"], {})
        print(f"Tool: {action['name']}")
        print(f"Arguments: {action['args']}")
        print(f"Allowed decisions: {review_config.get('allowed_decisions', ['approve', 'reject'])}")
        answer = input("Approve this subagent call? [y/n]: ").strip().lower()
        decision = {"type": "approve"} if answer == "y" else {"type": "reject"}
        decisions.append(decision)
        logger.info(
            "human decision recorded",
            extra={"tool": action["name"], "decision": decision["type"]},
        )

    return decisions


def _handle_human_review(interrupt_value: dict) -> dict:
    """Ask the user how to resolve a request_human_review escalation.

    Returns the resume payload in the shape human_review_tool.py's
    interrupt() call expects: {"action": ..., "notes": ...}.
    """
    print("\n=== HUMAN REVIEW ESCALATION ===")
    print(f"Reason: {interrupt_value.get('reason')}")
    print(f"Gaps summary: {interrupt_value.get('gaps_summary')}")
    print(f"Message: {interrupt_value.get('message')}")
    print("Review results.md / feedback.md in the workspace folder now if needed.")

    print("Options: [retry] let executor try again | [accept] accept results as-is | [stop] stop and report")
    action = input("Your decision [retry/accept/stop]: ").strip().lower()
    action = {"retry": "retry", "accept": "accept_as_is"}.get(action, "stop")
    notes = input("Any notes for the record (optional): ").strip()

    logger.info("human review decision recorded", extra={"action": action, "notes": notes})
    return {"action": action, "notes": notes}


def main(ticket_id: str):
    logger.info("demo run starting", extra={"ticket_id": ticket_id})

    workspace_dir = resolve_workspace_dir_name(ticket_id, config.WORKSPACE_BASE_DIR)
    print(f"Workspace for this run: {workspace_dir}/")

    agent = build_orchestrator(workspace_dir, checkpointer=_build_checkpointer())
    
    print(agent.get_graph().draw_mermaid())

    run_config = {"configurable": {"thread_id": ticket_id}}
    if config.CHECKPOINTER_BACKEND == "agentcore":
        run_config["configurable"]["actor_id"] = "jira_deep_agent_orchestrator"

    user_message = {
        "role": "user",
        "content": (
            f"A Jira ticket was created or updated: {ticket_id}. "
            f"Work the ticket end to end following your instructions."
        ),
    }

    print(f"\n=== Running orchestrator for {ticket_id} (workspace: {workspace_dir}/) ===\n")

    stream_input = {"messages": [user_message]}

    # Loop: run a leg with streaming, check for a pause, resolve it, repeat.
    while True:
        stream = _stream_run(agent, stream_input, run_config)

        if not stream.interrupted:
            break

        interrupt_value = stream.interrupts[0].value

        if "action_requests" in interrupt_value:
            decisions = _handle_task_approval(interrupt_value)
            stream_input = Command(resume={"decisions": decisions})
        elif interrupt_value.get("type") == "human_review_request":
            resume_payload = _handle_human_review(interrupt_value)
            stream_input = Command(resume=resume_payload)
        else:
            # Unknown interrupt shape -- print it raw so the demo doesn't
            # silently hang, and default to rejecting/stopping.
            print("\n=== UNRECOGNIZED INTERRUPT ===")
            print(interrupt_value)
            stream_input = Command(resume={"decisions": [{"type": "reject"}]})

    print(f"\n=== Run finished. Workspace artifacts are in {workspace_dir}/ ===")
    print("Look for plan.md, results.md, feedback.md (if any), and exec_summary.md.")

    logger.info("demo run finished", extra={"ticket_id": ticket_id, "workspace_dir": workspace_dir})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python demo_runner.py <JIRA_TICKET_ID>")
        sys.exit(1)

    main(sys.argv[1])