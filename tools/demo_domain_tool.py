# """
# Mock domain tool for the executor subagent.

# This is intentionally trivial. For the demo, the point is to prove the
# planner -> executor -> validator -> (retry) loop and the Jira in/out wiring,
# not to implement real Salesforce-to-Dynamics migration logic. Swap this out
# for real tools (repo access, metadata extraction, D365 API calls, etc.) once
# the pattern itself is signed off.
# """

# import random

# from langchain_core.tools import tool

# import config
# from logging_setup import get_logger

# logger = get_logger(__name__)

# # Toy lookup table standing in for a real Salesforce -> Dynamics 365 mapping.
# _MOCK_MAPPING = {
#     "Account": "Account (D365)",
#     "Contact": "Contact (D365)",
#     "Opportunity": "Opportunity (D365)",
#     "Custom_Object__c": "Custom Entity (D365)",
# }

# # Toy dependency graph standing in for real Salesforce metadata dependencies.
# # e.g. Opportunity depends on Account existing first; Custom_Object__c depends
# # on both Account and Contact.
# _MOCK_DEPENDENCIES = {
#     "Account": [],
#     "Contact": ["Account"],
#     "Opportunity": ["Account"],
#     "Custom_Object__c": ["Account", "Contact"],
# }

# # Per-process call counter for the deterministic forced-failure override.
# # Keyed by component name (case-normalized). Reset naturally on every new
# # process (i.e. every demo_runner.py invocation), which is what we want --
# # each fresh run gets the configured number of forced failures again.
# _forced_failure_call_counts: dict[str, int] = {}


# @tool
# def get_component_dependencies(component_name: str) -> str:
#     """Look up which other Salesforce components a given component depends on.

#     Use this during planning to determine correct migration order -- a
#     component must be migrated AFTER everything it depends on.

#     Args:
#         component_name: Name of the Salesforce component to check,
#             e.g. "Opportunity" or "Custom_Object__c".

#     Returns:
#         A string listing the component's direct dependencies, or noting that
#         it has none / is unknown.
#     """
#     logger.info("looking up component dependencies", extra={"component_name": component_name})

#     if component_name not in _MOCK_DEPENDENCIES:
#         result = f"'{component_name}' is not in the known dependency table -- treat as having no known dependencies, but flag for manual review."
#     else:
#         deps = _MOCK_DEPENDENCIES[component_name]
#         result = (
#             f"'{component_name}' has no dependencies -- can be migrated first."
#             if not deps
#             else f"'{component_name}' depends on: {', '.join(deps)}. Migrate those first."
#         )

#     logger.info(
#         "component dependency result",
#         extra={"component_name": component_name, "dependencies": _MOCK_DEPENDENCIES.get(component_name, [])},
#     )
#     return result


# def _forced_outcome(component_name: str) -> bool | None:
#     """Return the deterministic outcome for this call if the component is
#     the configured forced-failure target, or None if normal random logic
#     should apply (i.e. this isn't the configured component at all).

#     Returns:
#         False  -> force a partial failure (still under the configured count)
#         True   -> force a success (threshold already reached -- deterministic,
#                   not random, so the demo stays predictable once you've shown
#                   the failure count you wanted)
#         None   -> not the configured component; caller should use random logic
#     """
#     target = config.DEMO_FORCE_FAILURE_COMPONENT.strip()
#     if not target or target.lower() != component_name.lower():
#         return None

#     key = component_name.lower()
#     count_so_far = _forced_failure_call_counts.get(key, 0)

#     if count_so_far >= config.DEMO_FORCE_FAILURE_COUNT:
#         return True  # threshold already reached -- deterministic success now

#     _forced_failure_call_counts[key] = count_so_far + 1
#     return False  # still under threshold -- force a failure


# @tool
# def migrate_component(component_name: str) -> str:
#     """Simulate migrating one Salesforce component to its Dynamics 365 equivalent.

#     Args:
#         component_name: Name of the Salesforce component to migrate,
#             e.g. "Account" or "Custom_Object__c".

#     Returns:
#         A string describing the mocked migration outcome for this component.
#     """
#     logger.info("simulating component migration", extra={"component_name": component_name})

#     target = _MOCK_MAPPING.get(component_name, f"{component_name} (unmapped -- needs manual review)")

#     forced_outcome = _forced_outcome(component_name)
#     if forced_outcome is not None:
#         success = forced_outcome
#         logger.info(
#             "using deterministic forced outcome for demo",
#             extra={
#                 "component_name": component_name,
#                 "forced_success": success,
#                 "forced_failure_count_so_far": _forced_failure_call_counts.get(component_name.lower(), 0),
#                 "forced_failure_threshold": config.DEMO_FORCE_FAILURE_COUNT,
#             },
#         )
#     else:
#         # Randomly simulate an occasional incomplete migration so the
#         # validator has something real to catch during organic (non-forced)
#         # demo runs.
#         success = random.random() > 0.25

#     if success:
#         result = f"Migrated '{component_name}' -> '{target}' successfully."
#     else:
#         result = f"Partially migrated '{component_name}' -> '{target}': field-level mapping incomplete."

#     logger.info(
#         "component migration result",
#         extra={
#             "component_name": component_name,
#             "success": success,
#             "target": target,
#             "forced": forced_outcome is not None,
#         },
#     )
#     return result




"""
Mock domain tool for the executor subagent.

This is intentionally trivial. For the demo, the point is to prove the
planner -> executor -> validator -> (retry) loop and the Jira in/out wiring,
not to implement real Salesforce-to-Dynamics migration logic. Swap this out
for real tools (repo access, metadata extraction, D365 API calls, etc.) once
the pattern itself is signed off.
"""

import random

from langchain_core.tools import tool

import config
from logging_setup import get_logger

logger = get_logger(__name__)

# Toy lookup table standing in for a real Salesforce -> Dynamics 365 mapping.
_MOCK_MAPPING = {
    "Account": "Account (D365)",
    "Contact": "Contact (D365)",
    "Opportunity": "Opportunity (D365)",
    "Custom_Object__c": "Custom Entity (D365)",
}

# Toy dependency graph standing in for real Salesforce metadata dependencies.
# e.g. Opportunity depends on Account existing first; Custom_Object__c depends
# on both Account and Contact.
_MOCK_DEPENDENCIES = {
    "Account": [],
    "Contact": ["Account"],
    "Opportunity": ["Account"],
    "Custom_Object__c": ["Account", "Contact"],
}

# Per-process counter for the deterministic forced-failure override, keyed by
# component name (case-normalized). This counts VALIDATOR failures, not raw
# tool calls -- deliberately, since the executor may call migrate_component
# more than once for the same component within a single turn (e.g. it
# notices a partial result and immediately retries itself, before the
# validator ever runs again). If we counted tool calls, that kind of
# self-retry could burn through the whole forced-failure budget before the
# validator ever recorded a second failed verdict, so the human-escalation
# threshold would never actually trigger. Counting validator failures instead
# means the component keeps failing on every call until the validator itself
# has reported the configured number of failed verdicts.
# Reset naturally on every new process (i.e. every demo_runner.py
# invocation), which is what we want -- each fresh run gets the configured
# number of forced failures again.
_validator_failure_counts: dict[str, int] = {}


def note_validator_failure(component_name: str) -> None:
    """Called by validation_tool.py whenever submit_validation_verdict
    reports passed=False, so the forced-failure counter tracks actual
    validator failures rather than raw tool-call attempts."""
    key = component_name.lower()
    _validator_failure_counts[key] = _validator_failure_counts.get(key, 0) + 1
    logger.info(
        "recorded validator failure for demo forced-failure tracking",
        extra={"component_name": component_name, "validator_failure_count": _validator_failure_counts[key]},
    )


@tool
def get_component_dependencies(component_name: str) -> str:
    """Look up which other Salesforce components a given component depends on.

    Use this during planning to determine correct migration order -- a
    component must be migrated AFTER everything it depends on.

    Args:
        component_name: Name of the Salesforce component to check,
            e.g. "Opportunity" or "Custom_Object__c".

    Returns:
        A string listing the component's direct dependencies, or noting that
        it has none / is unknown.
    """
    logger.info("looking up component dependencies", extra={"component_name": component_name})

    if component_name not in _MOCK_DEPENDENCIES:
        result = f"'{component_name}' is not in the known dependency table -- treat as having no known dependencies, but flag for manual review."
    else:
        deps = _MOCK_DEPENDENCIES[component_name]
        result = (
            f"'{component_name}' has no dependencies -- can be migrated first."
            if not deps
            else f"'{component_name}' depends on: {', '.join(deps)}. Migrate those first."
        )

    logger.info(
        "component dependency result",
        extra={"component_name": component_name, "dependencies": _MOCK_DEPENDENCIES.get(component_name, [])},
    )
    return result


def _forced_outcome(component_name: str) -> bool | None:
    """Return the deterministic outcome for this call if the component is
    the configured forced-failure target, or None if normal random logic
    should apply (i.e. this isn't the configured component at all).

    Returns:
        False  -> force a partial failure (validator hasn't yet recorded
                  enough failures for this component to hit the threshold --
                  every tool call fails, no matter how many times the
                  executor calls it within one turn)
        True   -> force a success (the validator has already recorded
                  DEMO_FORCE_FAILURE_COUNT failures for this component --
                  deterministic, not random, so the demo stays predictable
                  once you've shown the failure count you wanted)
        None   -> not the configured component; caller should use random logic
    """
    target = config.DEMO_FORCE_FAILURE_COMPONENT.strip()
    if not target or target.lower() != component_name.lower():
        return None

    key = component_name.lower()
    validator_failures_so_far = _validator_failure_counts.get(key, 0)

    return validator_failures_so_far >= config.DEMO_FORCE_FAILURE_COUNT


@tool
def migrate_component(component_name: str) -> str:
    """Simulate migrating one Salesforce component to its Dynamics 365 equivalent.

    Args:
        component_name: Name of the Salesforce component to migrate,
            e.g. "Account" or "Custom_Object__c".

    Returns:
        A string describing the mocked migration outcome for this component.
    """
    logger.info("simulating component migration", extra={"component_name": component_name})

    target = _MOCK_MAPPING.get(component_name, f"{component_name} (unmapped -- needs manual review)")

    forced_outcome = _forced_outcome(component_name)
    if forced_outcome is not None:
        success = forced_outcome
        logger.info(
            "using deterministic forced outcome for demo",
            extra={
                "component_name": component_name,
                "forced_success": success,
                "validator_failure_count_so_far": _validator_failure_counts.get(component_name.lower(), 0),
                "forced_failure_threshold": config.DEMO_FORCE_FAILURE_COUNT,
            },
        )
    else:
        # Randomly simulate an occasional incomplete migration so the
        # validator has something real to catch during organic (non-forced)
        # demo runs.
        success = True

    if success:
        result = f"Migrated '{component_name}' -> '{target}' successfully."
    else:
        result = f"Partially migrated '{component_name}' -> '{target}': field-level mapping incomplete."

    logger.info(
        "component migration result",
        extra={
            "component_name": component_name,
            "success": success,
            "target": target,
            "forced": forced_outcome is not None,
        },
    )
    return result