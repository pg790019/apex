# # diag_subgraph_stream.py
# """
# Bypasses deep-agents-ui entirely. Talks straight to the LangGraph server
# via the Python SDK to check whether subagent events are actually being
# emitted at the server/API layer, independent of any frontend behavior.
# """
# import asyncio
# from langgraph_sdk import get_client

# LANGGRAPH_SERVER_URL = "http://localhost:2024"
# ASSISTANT_ID = "jira_orchestrator"


# async def main():
#     client = get_client(url=LANGGRAPH_SERVER_URL)
#     thread = await client.threads.create()

#     saw_subgraph_event = False

#     async for chunk in client.runs.stream(
#         thread["thread_id"],
#         ASSISTANT_ID,
#         input={"messages": [{"role": "human", "content": "work on jira issue KAN-9 AND COMPLETE THE TASK"}]},
#         stream_mode=["updates", "messages"],
#         stream_subgraphs=True,
#     ):
#         # A subgraph-sourced event has "|" in the event name, e.g. "messages|tools:call_abc"
#         is_subgraph = "|" in chunk.event
#         if is_subgraph:
#             saw_subgraph_event = True
#         print(f"event={chunk.event!r} is_subgraph={is_subgraph}")

#     print("\n--- RESULT ---")
#     print("Saw at least one subgraph-namespaced event:", saw_subgraph_event)


# asyncio.run(main())

"""
Run this instead of / alongside the previous script. Same setup, but
dumps the RAW payload of a couple of messages/partial events in full,
so we see the actual shape instead of guessing field names.
"""
import asyncio, json
from langgraph_sdk import get_client

LANGGRAPH_SERVER_URL = "http://localhost:2024"
ASSISTANT_ID = "jira_orchestrator"


async def main():
    client = get_client(url=LANGGRAPH_SERVER_URL)
    thread = await client.threads.create()
    print("Thread created:", thread["thread_id"], flush=True)

    dumped = 0
    async for chunk in client.runs.stream(
        thread["thread_id"],
        ASSISTANT_ID,
        input={"messages": [{"role": "human", "content": "work on jira issue KAN-9 AND COMPLETE THE TASK"}]},
        stream_mode=["updates", "messages"],
        stream_subgraphs=True,
    ):
        print("chunk event:", chunk.event, flush=True)   # TEMP — confirms events are arriving at all
        if chunk.event == "messages/partial" and dumped < 3:
            print(f"--- messages/partial raw dump #{dumped} ---", flush=True)
            print(json.dumps(chunk.data, indent=2, default=str)[:3000], flush=True)
            print(flush=True)
            dumped += 1
        if dumped >= 3:
            break


asyncio.run(main())