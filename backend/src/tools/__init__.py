"""Tool registry.

Aggregates every tool the agent can call and exposes:
- `TOOL_SCHEMAS`: the list passed to the LLM via the native `tools` parameter.
- `execute_tool`: dispatches a validated tool call to its implementation.

Adding a new tool = add its schema + executor here. Nothing else changes.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import sandbox_service
from src.tools.edit_tool import FILE_EDITOR_SCHEMA, file_editor
from src.tools.file_read import FILE_READ_SCHEMA, file_read
from src.tools.file_write import FILE_WRITE_SCHEMA, file_write
from src.tools.insert_after_line import INSERT_AFTER_LINE_SCHEMA, insert_after_line

# Native tool schemas passed directly to the LLM `tools` parameter.
TOOL_SCHEMAS: list[dict] = [
    FILE_WRITE_SCHEMA,
    FILE_READ_SCHEMA,
    FILE_EDITOR_SCHEMA,
    INSERT_AFTER_LINE_SCHEMA,
]


async def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    *,
    sandbox_id: str,
    e2b_api_key: str,
    execution_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Execute a tool by name against the active sandbox.

    Returns a structured dict: {"ok": bool, "result": str, "meta": {...}}.
    Errors are returned (never raised) so the agent loop can feed them back to
    the LLM for self-correction.
    """
    execution_context = execution_context or {}
    read_files = execution_context.setdefault("read_files", set())

    if name == "file_write":
        return await file_write(
            sandbox_service,
            sandbox_id=sandbox_id,
            e2b_api_key=e2b_api_key,
            **arguments,
        )
    if name == "file_read":
        result = await file_read(
            sandbox_service,
            sandbox_id=sandbox_id,
            e2b_api_key=e2b_api_key,
            **arguments,
        )
        if result.get("ok") and isinstance(arguments.get("file_path"), str):
            read_files.add(arguments["file_path"])
        return result
    if name == "file_editor":
        return await file_editor(
            sandbox_service,
            sandbox_id=sandbox_id,
            e2b_api_key=e2b_api_key,
            **arguments,
        )
    if name == "insert_after_line":
        return await insert_after_line(
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
