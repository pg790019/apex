"""
Webhook receiver: Jira "issue created" -> new LangGraph thread + run.

Scope (per current requirements): trigger ONLY on new ticket creation.
Configure the Jira webhook to fire on "Issue: created" ONLY (not "updated"),
so this never sees the agent's own comments/transitions.

Not production-safe: no signature verification, no dedup. Fine for
demoing the end-to-end flow.
"""

import logging

from fastapi import FastAPI, Request
from langgraph_sdk import get_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_server")

app = FastAPI()

LANGGRAPH_URL = "http://localhost:2024"
ASSISTANT_ID = "jira_orchestrator"  # matches the key in langgraph.json


@app.post("/webhooks/jira")
async def jira_webhook(request: Request):
    payload = await request.json()
    logger.info(f"Webhook event : \n {payload.get("webhookEvent")}")
    ticket_key = payload.get("issue", {}).get("key")
    if not ticket_key:
        logger.warning("no issue.key in payload, ignoring")
        return {"status": "ignored", "reason": "no ticket key found"}

    logger.info("received Jira issue_created webhook", extra={"ticket_key": ticket_key})

    client = get_client(url=LANGGRAPH_URL)

    # New thread per ticket -- thread_id becomes the UI's grouping key.
    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    user_message = {
        "role": "user",
        "content": (
            f"A Jira ticket was created: {ticket_key}. "
            f"Work the ticket end to end following your instructions."
        ),
    }

    run = await client.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        input={"messages": [user_message]},
        stream_subgraphs=True,   # NEW — emit events from the task tool's subgraph (planner/executor/validator)
        stream_resumable=True,  # NEW — lets deep-agents-ui's later joinStream() pick up the full backlog
    )

    logger.info(
        "started run for ticket",
        extra={"ticket_key": ticket_key, "thread_id": thread_id, "run_id": run["run_id"]},
    )

    return {"status": "started", "thread_id": thread_id, "run_id": run["run_id"]}