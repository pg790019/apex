"""
Workspace folder resolution.

Deep agents' FilesystemBackend just reads/writes wherever you point its
root_dir -- it has no concept of "versioned per-ticket runs." That logic is
plain Python, applied once before the agent is built for a given ticket.

Folder naming: agent-work-{ticket_id} for the first run on a ticket, then
agent-work-{ticket_id}-v1, -v2, ... for subsequent runs, so re-running the
demo against the same ticket never clobbers a previous run's artifacts.
"""

import os

from logging_setup import get_logger

logger = get_logger(__name__)


def resolve_workspace_dir_name(ticket_id: str, base_dir: str) -> str:
    """Return the workspace folder NAME (not full path) to use for this run.

    The folder is created on disk (empty) as part of resolving it, so the
    check-then-create is atomic-ish for a single-process demo (not
    concurrency-safe -- fine for this use case).
    """
    base_name = f"agent-work-{ticket_id}"
    candidate = base_name
    version = 0

    while os.path.isdir(os.path.join(base_dir, candidate)):
        version += 1
        candidate = f"{base_name}-v{version}"

    full_path = os.path.join(base_dir, candidate)
    os.makedirs(full_path, exist_ok=True)

    logger.info(
        "resolved workspace directory",
        extra={"ticket_id": ticket_id, "workspace_dir": candidate, "full_path": full_path},
    )
    return candidate
