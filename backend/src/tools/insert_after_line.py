"""insert_after_line tool.

Inserts a text block immediately after a specific line number in an existing file
inside the active E2B sandbox. The insertion logic executes inside the sandbox
via a Python command so the mutation happens within the user's isolated runtime.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService

INSERT_AFTER_LINE_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "insert_after_line",
        "description": "Insert text after a specific line in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path of the file to modify.",
                },
                "line_number": {
                    "type": "integer",
                    "description": "The line number after which the content should be inserted. examples: line number 37 inserts after line 37. line number 26 inserts after line 26.",
                },
                "content": {
                    "type": "string",
                    "description": "The exact text or code block to insert. The content will be inserted AFTER the line",
                },
            },
            "required": ["file_path", "line_number", "content"],
        },
    },
}


async def insert_after_line(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    file_path: str,
    line_number: int,
    content: str,
) -> Dict[str, Any]:
    """Insert `content` after `line_number` in `file_path` inside the sandbox."""
    if not isinstance(file_path, str) or not file_path.strip():
        return {
            "ok": False,
            "result": "Error: 'file_path' is required and must be a non-empty string.",
            "meta": {"tool": "insert_after_line"},
        }
    if not file_path.startswith("/"):
        return {
            "ok": False,
            "result": "Error: 'file_path' must be an absolute path.",
            "meta": {"tool": "insert_after_line", "file_path": file_path},
        }
    if not isinstance(line_number, int) or isinstance(line_number, bool) or line_number < 1:
        return {
            "ok": False,
            "result": "Error: 'line_number' is required and must be an integer greater than or equal to 1.",
            "meta": {"tool": "insert_after_line", "file_path": file_path},
        }
    if not isinstance(content, str):
        return {
            "ok": False,
            "result": "Error: 'content' must be a string.",
            "meta": {"tool": "insert_after_line", "file_path": file_path},
        }

    try:
        payload = await sandbox_service.insert_after_line(
            sandbox_id,
            e2b_api_key,
            file_path=file_path,
            line_number=line_number,
            content=content,
        )
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error executing insert_after_line for '{file_path}': {exc}",
            "meta": {
                "tool": "insert_after_line",
                "file_path": file_path,
                "line_number": line_number,
            },
        }

    if not payload.get("ok"):
        return {
            "ok": False,
            "result": payload.get("error") or f"Error: failed to insert content after line {line_number}.",
            "meta": {
                "tool": "insert_after_line",
                "file_path": file_path,
                "line_number": line_number,
                **{k: v for k, v in payload.items() if k not in {"ok", "error"}},
            },
        }

    inserted_line_count = payload.get("inserted_line_count")
    return {
        "ok": True,
        "result": f"Successfully inserted content after line {line_number} in {file_path}.",
        "meta": {
            "tool": "insert_after_line",
            "file_path": file_path,
            "line_number": line_number,
            "inserted_line_count": inserted_line_count,
            **{k: v for k, v in payload.items() if k != "ok"},
        },
    }