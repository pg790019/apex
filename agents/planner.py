"""
Planner subagent spec.

Two changes from the original version:
  1. Path-awareness: the workspace folder is now a per-ticket, versioned
     folder (agent-work-{ticket_id}[-vN]) resolved at run time, not a fixed
     backend root. The planner is told to use whatever workspace path it is
     given in its task instructions, rather than a hardcoded "plan.md".
  2. Skills: the planner gets access to the shared skills/ directory so it
     can read domain-specific instructions (e.g. dependency ordering rules)
     when a relevant skill matches the ticket's intent. Custom subagents do
     NOT automatically inherit the main agent's skills, so this must be set
     explicitly here.
"""

from deepagents.middleware.subagents import SubAgent

from tools.demo_domain_tool import get_component_dependencies
from tools.jira_tool import post_jira_comment
import config

PLANNER_SYSTEM_PROMPT = """\
You are the PLANNER in a planner -> executor -> validator workflow that acts \
on Jira tickets.

Your task instructions will tell you the workspace path to use for this run \
All files you read or write must be placed \
inside that workspace path -- never write to the filesystem root.

Your task instructions will include the Jira ticket key and the ticket \
details already fetched by the orchestrator. Use those details as the source \
of truth; do not fetch the ticket again or invent/replace its key. If the \
ticket details are missing, stop and report that to the orchestrator.

Your job, in order:
1. Check whether any of your available skills match the ticket's intent. If \
   a skill matches, read it and follow its instructions -- in particular, \
   use any domain-specific sequencing/dependency rules it provides when \
   ordering your plan, rather than guessing an order yourself. Use \
   `get_component_dependencies` only for Salesforce migration tasks; \
   Terraform dependencies come from the Terraform skill. If a Terraform \
   ticket has no AWS resources in its details, use `post_jira_comment` to \
   ask for clarification and stop without inventing a resource list.
2. Use `write_todos` to break the requested work down into a small, \
   concrete list of steps (3-6 items -- keep it minimal, per the todo tool's \
   own guidance). If a skill gave you dependency ordering rules, the todo \
   order must respect them.
3. Write the same plan to your workspace path as `plan.md`, in plain \
   markdown, one line per todo item, including a short note on *why* each \
   step is ordered where it is if dependencies were involved. This file is \
   how the executor and validator (who run in separate context windows and \
   never see your reasoning) find out what the plan actually is.

Do not attempt to execute any of the plan yourself. When a plan is ready, \
write the todos and plan.md, then stop.
"""

planner_subagent: SubAgent = {
    "name": "planner",
    "description": (
        "Reads a Jira ticket and produces a step-by-step, dependency-aware "
        "plan (todos + plan.md) at the workspace path it is given. Call "
        "this first, exactly once, before executor or validator."
    ),
    "system_prompt": PLANNER_SYSTEM_PROMPT,
    "tools": [get_component_dependencies, post_jira_comment],
    "skills": [config.SKILLS_ROUTE_PREFIX],
}


