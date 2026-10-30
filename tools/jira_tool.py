"""
Jira integration tools.

These are plain
LangChain @tool-wrapped functions around the Jira REST API v3. 

All three tools are attached to the orchestrator (and the planner, for
read access) so the LLM can call them directly like any other tool.
"""

import requests
from requests.auth import HTTPBasicAuth
from langchain_core.tools import tool

import config
from logging_setup import get_logger

logger = get_logger(__name__)

_AUTH = HTTPBasicAuth(config.JIRA_EMAIL, config.JIRA_API_TOKEN)
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


@tool
def get_jira_ticket(ticket_id: str) -> str:
    """Fetch a Jira ticket's summary, description, status, and comments.

    Args:
        ticket_id: The Jira issue key, e.g. "PROJ-123".

    Returns:
        A plain-text rendering of the ticket's summary, description, status,
        and up to the 10 most recent comments, for use as planning context.
    """
    url = f"{config.JIRA_BASE_URL}/rest/api/3/issue/{ticket_id}"
    logger.info("fetching jira ticket", extra={"ticket_id": ticket_id, "url": url})

    try:
        resp = requests.get(url, headers=_HEADERS, auth=_AUTH, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("failed to fetch jira ticket", extra={"ticket_id": ticket_id})
        return f"ERROR: could not fetch ticket {ticket_id} from Jira. Check JIRA_BASE_URL/credentials."

    data = resp.json()
    fields = data.get("fields", {})
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "unknown")

    # Jira's description is Atlassian Document Format (ADF), not plain text.
    # We do a shallow best-effort text extraction rather than pulling in a
    # full ADF renderer -- good enough for agent context.
    description = _extract_plain_text(fields.get("description"))

    comments_raw = fields.get("comment", {}).get("comments", [])[-10:]
    comments = [
        f"- ({c.get('author', {}).get('displayName', 'unknown')}): "
        f"{_extract_plain_text(c.get('body'))}"
        for c in comments_raw
    ]

    rendered = (
        f"Ticket: {ticket_id}\n"
        f"Status: {status}\n"
        f"Summary: {summary}\n"
        f"Description:\n{description}\n\n"
        f"Recent comments:\n" + ("\n".join(comments) if comments else "(none)")
    )

    logger.info(
        "fetched jira ticket",
        extra={"ticket_id": ticket_id, "status": status, "comment_count": len(comments)},
    )
    return rendered


@tool
def post_jira_comment(ticket_id: str, comment: str) -> str:
    """Post a comment on a Jira ticket.

    Args:
        ticket_id: The Jira issue key, e.g. "PROJ-123".
        comment: Plain-text comment body to post.

    Returns:
        A confirmation string, or an error message if the call failed.
    """
    url = f"{config.JIRA_BASE_URL}/rest/api/3/issue/{ticket_id}/comment"
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ],
        }
    }

    logger.info("posting jira comment", extra={"ticket_id": ticket_id, "comment_length": len(comment)})

    try:
        resp = requests.post(url, headers=_HEADERS, auth=_AUTH, json=body, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("failed to post jira comment", extra={"ticket_id": ticket_id})
        return f"ERROR: could not post comment to ticket {ticket_id}."

    logger.info("posted jira comment", extra={"ticket_id": ticket_id})
    return f"Comment posted to {ticket_id}."


@tool
def transition_jira_ticket(ticket_id: str, transition_name: str) -> str:
    """Move a Jira ticket to a new status (e.g. "Done", "In Progress").

    Args:
        ticket_id: The Jira issue key, e.g. "PROJ-123".
        transition_name: The exact name of the target Jira workflow
            transition, as configured in the project's workflow (e.g. "Done").

    Returns:
        A confirmation string, or an error message if the transition name
        was not found or the call failed.
    """
    base = f"{config.JIRA_BASE_URL}/rest/api/3/issue/{ticket_id}/transitions"
    logger.info(
        "transitioning jira ticket",
        extra={"ticket_id": ticket_id, "transition_name": transition_name},
    )

    try:
        resp = requests.get(base, headers=_HEADERS, auth=_AUTH, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("failed to list jira transitions", extra={"ticket_id": ticket_id})
        return f"ERROR: could not list transitions for ticket {ticket_id}."

    transitions = resp.json().get("transitions", [])
    match = next(
        (t for t in transitions if t.get("name", "").lower() == transition_name.lower()),
        None,
    )
    if not match:
        available = [t.get("name") for t in transitions]
        logger.warning(
            "transition name not found",
            extra={"ticket_id": ticket_id, "requested": transition_name, "available": available},
        )
        return f"ERROR: transition '{transition_name}' not available. Options: {available}"

    try:
        resp = requests.post(
            base, headers=_HEADERS, auth=_AUTH, json={"transition": {"id": match["id"]}}, timeout=15
        )
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("failed to apply jira transition", extra={"ticket_id": ticket_id})
        return f"ERROR: could not apply transition '{transition_name}' to {ticket_id}."

    logger.info("transitioned jira ticket", extra={"ticket_id": ticket_id, "transition_name": transition_name})
    return f"Ticket {ticket_id} moved to '{transition_name}'."


def _extract_plain_text(adf_node) -> str:
    """Best-effort plain-text extraction from an Atlassian Document Format node."""
    if not adf_node:
        return ""
    if isinstance(adf_node, str):
        return adf_node

    texts: list[str] = []

    def _walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text" and "text" in node:
                texts.append(node["text"])
            for child in node.get("content", []) or []:
                _walk(child)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(adf_node)
    return " ".join(texts).strip()
