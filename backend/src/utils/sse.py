"""Server-Sent Events (SSE) helpers.

Encodes structured agent events into the SSE wire format. Each event is a JSON
payload carrying a discriminated `type` so the frontend can route it precisely
(token, tool_call, tool_result, iteration, sandbox, error, done, ...).
"""
from __future__ import annotations

from typing import Any, Dict

import orjson


def sse_event(event_type: str, data: Dict[str, Any] | None = None) -> str:
    """Serialise a single SSE message.

    The payload is delivered as a JSON object on the default `message` event so
    the browser EventSource / fetch-stream reader can parse it uniformly.
    """
    payload: Dict[str, Any] = {"type": event_type}
    if data:
        payload.update(data)
    body = orjson.dumps(payload).decode("utf-8")
    return f"data: {body}\n\n"


def sse_comment(text: str) -> str:
    """Emit an SSE comment line (used as a keep-alive heartbeat)."""
    return f": {text}\n\n"
