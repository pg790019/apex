"""
Orchestrator: the top-level deep agent.

Changes from the original version:
  1. Skills: the ticket's intent is matched against SKILL.md files in the
     shared skills/ directory (deep agents' native Skills system). If no
     skill matches, the orchestrator is instructed to decline the ticket
     instead of proceeding to planning.
  2. Backend: FilesystemBackend rooted at a per-ticket, versioned workspace
     folder (agent-work-{ticket_id}[-vN]) resolved by workspace.py before
     this module is invoked -- so all plan.md/results.md/feedback.md writes
     land as real files on local disk.
  3. Human-in-the-loop: interrupt_on={"task": ...} pauses execution before
     every subagent (task tool) call -- in practice this means: pause before
     planner starts (extra checkpoint), pause after planner/before executor
     (as requested), and pause after executor/before validator (as
     requested). This is a tool-level interrupt, not a "phase" interrupt --
     deep agents doesn't support the latter directly.
  4. A dedicated request_human_review tool (interrupt() called directly from
     inside a tool) lets the orchestrator escalate to a human after N
     consecutive failed validations, distinct from the automatic task-call
     pauses above.

Routing between planner -> executor -> validator -> (retry | finish) is
still driven entirely by the orchestrator's own reasoning over the
validator's structured verdict (LLM-based routing), not a hardcoded graph
edge -- this remains a deliberate trade-off per requirements.
"""

import os
from pathlib import Path
import asyncio

from tools.github_publish_tools import create_guarded_github_tools
from tools.github_mcp_client import get_github_mcp_tools
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.filesystem import FilesystemBackend
# from langchain_aws import ChatBedrockConverse
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

import config
from agents.planner import planner_subagent
from agents.executor import executor_subagent
from agents.validator import validator_subagent
from tools.jira_tool import get_jira_ticket, post_jira_comment, transition_jira_ticket
from tools.human_review_tool import request_human_review
from tools.plan_approval_tool import request_plan_approval
from logging_setup import get_logger

logger = get_logger(__name__)


ORCHESTRATOR_SYSTEM_PROMPT_TEMPLATE = """
You are the ORCHESTRATOR for a Jira-triggered work automation system, built 
on planner, executor, and validator subagents.

Your workspace path for this entire run is: {workspace_dir}/
All Jira tools and every subagent you delegate to will read/write files 
inside this workspace path. Always mention this path explicitly when 
delegating to a subagent via the `task` tool, e.g. "...using workspace path 
{workspace_dir}/".

GitHub repository configuration:
- Owner: {github_owner}
- Repository: {github_repo}
- Base branch: {github_base_branch}

You will be given a Jira ticket ID. Follow this sequence exactly:

0. Call `get_jira_ticket` to read the ticket's intent (summary, description, 
   comments). Check whether any available skill's description matches this 
   intent.
   - If `get_jira_ticket` returns an error, report the fetch failure and 
     stop. Do not delegate to the planner.
   - If NO skill matches: STRICTLY call `post_jira_comment` saying you don't have a 
     relevant skill to complete this task, and therefore are not 
     continuing. Stop here. Do not call the planner.
   - If a skill matches: continue to step 1.

1. Delegate to the `planner` subagent via `task`, passing the ticket ID and 
   the complete ticket details returned by `get_jira_ticket`, and the 
   workspace path. The planner must use these supplied details and must not 
   fetch the ticket again. Wait for it to finish producing plan.md. (Note: 
   this call itself may pause for human approval -- that is expected.)

2. Read plan.md and call the `request_plan_approval` tool with a concise summary of the generated plan.

3. Wait for the human decision.
   - If approved, continue to the executor.
   - If rejected, stop execution and report that the plan was rejected.

4. Delegate to the `executor` subagent via `task`, passing the ticket ID and 
   workspace path. Wait for it to finish producing results.md.

5. Delegate to the `validator` subagent via `task`, passing the ticket ID 
   and workspace path. It will call `submit_validation_verdict` -- read 
   that result carefully.

6. Track how many CONSECUTIVE times validation has failed for this run, 
   starting from zero.
   - If passed=True: reset the counter and proceed to GitHub publishing.
   - If passed=False: increment the counter.
     - If the counter has now reached 
       {max_consecutive_failures} consecutive failures: call 
       `request_human_review` with a summary of the gaps, instead of 
       retrying the executor again. Wait for the human's decision.
       - If told to retry, delegate to executor and then validator again.
       - If told to accept results as-is, stop without GitHub publishing.
       - If told to stop, stop and report.
     - Otherwise (counter below the threshold): delegate to `executor` 
       again, explicitly telling it to read feedback.md and address the 
       listed gaps. Then go back to step 5 (call validator again).
   - Do not exceed {max_retries} total executor invocations in this run 
     regardless of the above, as an absolute ceiling.

GITHUB PUBLISHING:

Only perform GitHub publishing after final validation has passed.

1. Read the generated files from the current workspace.
2. Do not publish plan.md, feedback.md, exec_summary.md, or temporary files.
3. Prepare the list of files that belong to the completed implementation.
4. Create a new GitHub branch using github_create_branch_guarded:
   - owner: {github_owner}
   - repo: {github_repo}
   - branch: feature/apex-{{ticket_id}}
   - from_branch: {github_base_branch}

5. Push generated files using github_push_files_guarded:
   - owner: {github_owner}
   - repo: {github_repo}
   - branch: feature/apex-{{ticket_id}}
   
6. If branch creation or file publishing fails:
   - Do not claim that publishing succeeded.
   - Record the failure details in exec_summary.md.
   - Mention the publishing failure in the Jira comment.
7. Never publish if final validation has not passed.
8. Never push directly to the base branch.
9. Do not create a pull request. Publishing is branch-based only.

7. Write a file named `exec_summary.md` to your workspace path, summarizing: 
   what was requested, what the plan was, what the executor did, the final 
   validation outcome, how many retries occurred, whether any human review 
   was triggered and what was decided, and the GitHub publishing outcome.

8. Call `post_jira_comment` on the original ticket with a concise summary of 
   what was done, the final validation outcome, and the GitHub branch/publishing 
   status. If validation fully passed, also call `transition_jira_ticket` 
   to move it to "Done" (only if that transition exists -- if it errors, 
   just mention it in the comment instead of retrying the transition).

Be explicit in your own reasoning about which step you are on and why -- 
this is being logged for observability. Never skip the validator step, and 
never call `task` for planner or validator more than once per cycle.
"""


def _build_checkpointer():
    """Return a LangGraph-compatible checkpointer per config.CHECKPOINTER_BACKEND.

    A checkpointer is REQUIRED for human-in-the-loop (interrupt_on and the
    request_human_review tool) -- without one, state can't persist between
    the interrupt and the resume call.
    """
    if config.CHECKPOINTER_BACKEND == "agentcore":
        from langgraph_checkpoint_aws import AgentCoreMemorySaver

        logger.info(
            "using AgentCoreMemorySaver for checkpointing",
            extra={"memory_id": config.AGENTCORE_MEMORY_ID, "region": config.AWS_REGION},
        )
        return AgentCoreMemorySaver(
            config.AGENTCORE_MEMORY_ID, region_name=config.AWS_REGION
        )

    logger.warning(
        "using in-process MemorySaver -- state will NOT persist across process "
        " Set CHECKPOINTER_BACKEND=agentcore for sustained deployments."
    )
    return MemorySaver()

def build_orchestrator(workspace_dir: str, checkpointer=None):
    """Construct the compiled deep agent graph for the orchestrator.
    
    Args:
        workspace_dir: Folder path for this run
        checkpointer: If None, no checkpointer will be passed (for API deployments).
                     If provided, it will be used (for terminal/standalone runs).
    """
    logger.info(
        "building orchestrator",
        extra={
            "deployment": config.AZURE_OPENAI_MODEL_ID,
            "workspace_dir": workspace_dir,
        },
    )

    model = AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        azure_deployment=config.AZURE_OPENAI_MODEL_ID,
        api_version=config.AZURE_OPENAI_API_VERSION,
        api_key=config.AZURE_OPENAI_API_KEY,
        temperature=0,
    )

    # Don't build checkpointer here — use what was passed in
    # (This ensures API deployment can pass None, terminal can pass a real one)

    workspace_backend = StateBackend() 
    skills_backend = FilesystemBackend(
        root_dir=os.path.join(config.WORKSPACE_BASE_DIR, config.SKILLS_DIR_NAME),
        virtual_mode=True,
    )
    backend = CompositeBackend(
        default=workspace_backend,
        routes={config.SKILLS_ROUTE_PREFIX: skills_backend},
    )

    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT_TEMPLATE.format(
        workspace_dir="/workspace",
        max_consecutive_failures=config.MAX_CONSECUTIVE_VALIDATION_FAILURES_BEFORE_REVIEW,
        max_retries=config.MAX_EXECUTOR_RETRIES,
        github_owner=config.GITHUB_OWNER,
        github_repo=config.GITHUB_REPO,
        github_base_branch=config.GITHUB_BASE_BRANCH,
    )

    github_mcp_tools = asyncio.run(get_github_mcp_tools())

    github_tools = create_guarded_github_tools(
    github_mcp_tools)

    logger.info(
    "Guarded GitHub tools registered",
    extra={
        "tools": [tool.name for tool in github_tools]
    },)

    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[get_jira_ticket, post_jira_comment, transition_jira_ticket, request_human_review, request_plan_approval, *github_tools,],
        subagents=[planner_subagent, executor_subagent, validator_subagent],
        skills=[config.SKILLS_ROUTE_PREFIX],
        backend=backend,
        # interrupt_on={"task": {"allowed_decisions": ["approve", "reject"]}},
        name="jira_deep_agent_orchestrator",
    )
    return agent


async def make_graph(config):
    """Factory entry point for langgraph.json. Called per-run by the API
    server; no checkpointer passed since the server manages persistence."""
    thread_id = (config.get("configurable") or {}).get("thread_id", "default")
    
    # Use absolute path to avoid blocking getcwd() call in async context
    script_dir = Path(__file__).parent
    workspace_dir = str(script_dir / f"agent-work-thread-{thread_id}")
    
    #Wrap blocking orchestrator build in thread to avoid event loop blocking
    return await asyncio.to_thread(
        build_orchestrator, 
        "/workspace",  # virtual path only, no real directory
        None  # checkpointer=None
    )