"""
Structured logging setup.

Emits one JSON object per line to stdout.
  1. It's easy for a human to read during local demo runs.
  2. It's exactly the shape CloudWatch Logs / AgentCore Observability expects
     when scraping stdout for structured log ingestion -- no changes needed
     when this moves from a local process to an AgentCore Runtime deployment.

Usage:
    from logging_setup import get_logger
    logger = get_logger(__name__)
    logger.info("ticket fetched", extra={"ticket_id": "ABC-123", "stage": "planner"})
"""

import json
import logging
import sys
from datetime import datetime, timezone

# Fields that exist on every LogRecord by default -- anything NOT in this set
# that shows up on the record came from a caller's extra={...} dict, and we
# fold it into the JSON output as its own field.
_STANDARD_RECORD_FIELDS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Pull through any extra={...} fields callers attached to this record.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger configured with the JSON formatter.

    Safe to call repeatedly (e.g. once per module via get_logger(__name__));
    handlers are only attached once per logger name.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        # Don't double-log through the root logger as well.
        logger.propagate = False

    return logger
