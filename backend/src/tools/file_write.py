"""file_write tool.

Creates or fully overwrites a file at an absolute path inside the E2B sandbox.
No size or type limits are imposed by this tool.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Exact native tool schema as specified in the requirements.
FILE_WRITE_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "file_write",
        "description": "Create or overwrite a file at the given path inside the sandbox. Use for creating new files or fully rewriting existing ones.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path starting with /home/user/. Example: /home/user/project/src/App.tsx",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}


async def file_write(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    file_path: str,
    content: str,
) -> Dict[str, Any]:
    """Write `content` to `file_path` in the sandbox.

    Returns a structured result. On failure, returns a structured error string
    so the agent can continue its loop and self-correct.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return {
            "ok": False,
            "result": "Error: 'file_path' is required and must be a non-empty string.",
            "meta": {"tool": "file_write"},
        }
    if not isinstance(content, str):
        return {
            "ok": False,
            "result": "Error: 'content' must be a string.",
            "meta": {"tool": "file_write", "file_path": file_path},
        }

    try:
        await sandbox_service.write_file(sandbox_id, e2b_api_key, file_path, content)
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error writing file '{file_path}': {exc}",
            "meta": {"tool": "file_write", "file_path": file_path},
        }

    byte_len = len(content.encode("utf-8"))
    return {
        "ok": True,
        "result": f"Successfully wrote {byte_len} bytes to {file_path}.",
        "meta": {"tool": "file_write", "file_path": file_path, "bytes": byte_len},
    }
