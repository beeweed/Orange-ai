"""Tool registry.

Aggregates every tool the agent can call and exposes:
- `TOOL_SCHEMAS`: the list passed to the LLM via the native `tools` parameter.
- `execute_tool`: dispatches a validated tool call to its implementation.

Adding a new tool = add its schema + executor here. Nothing else changes.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import sandbox_service
from src.tools.file_read import FILE_READ_SCHEMA, file_read
from src.tools.file_write import FILE_WRITE_SCHEMA, file_write

# Native tool schemas passed directly to the LLM `tools` parameter.
TOOL_SCHEMAS: list[dict] = [
    FILE_WRITE_SCHEMA,
    FILE_READ_SCHEMA,
]


async def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    *,
    sandbox_id: str,
    e2b_api_key: str,
) -> Dict[str, Any]:
    """Execute a tool by name against the active sandbox.

    Returns a structured dict: {"ok": bool, "result": str, "meta": {...}}.
    Errors are returned (never raised) so the agent loop can feed them back to
    the LLM for self-correction.
    """
    if name == "file_write":
        return await file_write(
            sandbox_service,
            sandbox_id=sandbox_id,
            e2b_api_key=e2b_api_key,
            **arguments,
        )
    if name == "file_read":
        return await file_read(
            sandbox_service,
            sandbox_id=sandbox_id,
            e2b_api_key=e2b_api_key,
            **arguments,
        )
    return {
        "ok": False,
        "result": f"Unknown tool: {name}",
        "meta": {"tool": name},
    }
