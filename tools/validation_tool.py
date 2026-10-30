# """
# Structured verdict tool for the validator subagent.

# The whole point of this tool: force the validator to report pass/fail plus
# gaps as a schema'd tool call instead of free-flowing prose. That's what lets
# the orchestrator's LLM-based routing reliably decide "retry the executor" vs
# "finish and report to Jira" -- it's reading a structured result, not trying
# to parse natural language for intent.
# """

# from langchain_core.tools import tool

# from logging_setup import get_logger

# logger = get_logger(__name__)


# @tool
# def submit_validation_verdict(passed: bool, gaps: list[str], summary: str) -> str:
#     """Report the outcome of validating the executor's work against the plan.

#     Call this exactly once as the final step of validation.

#     Args:
#         passed: True if the executor's results fully satisfy every item in
#             the plan. False if anything is missing, incorrect, or incomplete.
#         gaps: List of specific, actionable gaps the executor still needs to
#             address. Empty list if passed is True.
#         summary: One or two sentence human-readable summary of the
#             validation outcome, suitable for posting to Jira.

#     Returns:
#         A short acknowledgement string. The real signal is the structured
#         arguments this tool was called with -- the orchestrator reads those.
#     """
#     logger.info(
#         "validation verdict submitted",
#         extra={"passed": passed, "gap_count": len(gaps), "gaps": gaps},
#     )
#     status = "PASSED" if passed else "FAILED"
#     return f"Verdict recorded: {status}. Gaps: {gaps if gaps else 'none'}."


"""
Structured verdict tool for the validator subagent.

The whole point of this tool: force the validator to report pass/fail plus
gaps as a schema'd tool call instead of free-flowing prose. That's what lets
the orchestrator's LLM-based routing reliably decide "retry the executor" vs
"finish and report to Jira" -- it's reading a structured result, not trying
to parse natural language for intent.
"""




"""
Structured verdict tool for the validator subagent.
"""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

import config as app_config

from tools.demo_domain_tool import note_validator_failure
from tools.validation_gate import record_validation_verdict
from logging_setup import get_logger

logger = get_logger(__name__)


@tool
def submit_validation_verdict(
    passed: bool,
    gaps: list[str],
    summary: str,
    config: RunnableConfig,
) -> str:
    """Report the outcome of validating the executor's work."""

    logger.info(
        "Validation verdict submitted",
        extra={
            "passed": passed,
            "gaps": gaps,
            "summary": summary,
            "thread_id": config.get("configurable", {}).get("thread_id"),
        },
    )

    record_validation_verdict(config, passed)

    if (
        not passed
        and app_config.DEMO_FORCE_FAILURE_COMPONENT.strip()
    ):
        note_validator_failure(
            app_config.DEMO_FORCE_FAILURE_COMPONENT.strip()
        )

    status = "PASSED" if passed else "FAILED"

    return (
        f"Verdict recorded: {status}. "
        f"Gaps: {gaps if gaps else 'none'}."
    )

