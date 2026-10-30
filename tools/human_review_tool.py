"""
Human review escalation tool.

This is different from the interrupt_on={"task": ...} config used for the
plan-approval and execute-approval checkpoints. Those pause automatically
whenever the `task` tool is called, regardless of *why*. This tool instead
calls LangGraph's interrupt() primitive directly, so the orchestrator itself
decides *when* to pause (after N consecutive validation failures, per its
system prompt) rather than pausing on every tool call of a given name.

Requires a checkpointer on the agent (already configured in orchestrator.py).
"""

from langchain_core.tools import tool
from langgraph.types import interrupt

from logging_setup import get_logger

logger = get_logger(__name__)


@tool
def request_human_review(ticket_id: str, reason: str, gaps_summary: str) -> str:
    """Pause the workflow and ask a human to review the situation manually.

    Call this when automated validation has failed multiple consecutive
    times and continuing to retry the executor automatically is unlikely to
    help -- e.g. after 2 consecutive failed validation passes.

    Args:
        ticket_id: The Jira ticket this run is for.
        reason: Why you are escalating (e.g. "validation failed twice in a row").
        gaps_summary: A short summary of the gaps the validator has reported,
            so the human reviewer has context without reading every file.

    Returns:
        A string describing the human's decision once execution resumes.
    """
    logger.warning(
        "escalating to human review",
        extra={"ticket_id": ticket_id, "reason": reason, "gaps_summary": gaps_summary},
    )

    decision = interrupt(
        {
            "type": "human_review_request",
            "ticket_id": ticket_id,
            "reason": reason,
            "gaps_summary": gaps_summary,
            "message": (
                "Automated validation failed repeatedly. Please review "
                "results.md and feedback.md in the workspace folder, then "
                "decide how to proceed."
            ),
        }
    )

    logger.info(
        "human review decision received",
        extra={"ticket_id": ticket_id, "decision": decision},
    )

    action = decision.get("action", "stop") if isinstance(decision, dict) else "stop"
    notes = decision.get("notes", "") if isinstance(decision, dict) else ""

    if action == "retry":
        return f"Human reviewed and approved another executor retry. Notes: {notes or 'none'}"
    elif action == "accept_as_is":
        return f"Human reviewed and accepted current results as-is despite validation gaps. Notes: {notes or 'none'}"
    else:
        return f"Human reviewed and decided to stop the automated flow here. Notes: {notes or 'none'}"
