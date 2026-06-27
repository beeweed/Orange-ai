"""file_read tool.

Reads the content of an existing file from the E2B sandbox and returns it with
line numbers. If the path does not exist, returns a structured error so the
agent loop can continue and self-correct. No size limits are imposed.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Exact native tool schema as specified in the requirements.
FILE_READ_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "file_read",
        "description": "Read the content of an existing file from the sandbox. Returns content with line numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path starting with /home/user/. Example: /home/user/project/src/main.py",
                },
            },
            "required": ["file_path"],
        },
    },
}


def _with_line_numbers(text: str) -> str:
    """Prefix each line with a 1-based, right-aligned line number."""
    lines = text.splitlines()
    if not lines:
        return ""
    width = len(str(len(lines)))
    return "\n".join(f"{str(i).rjust(width)}\t{line}" for i, line in enumerate(lines, start=1))


async def file_read(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    file_path: str,
) -> Dict[str, Any]:
    """Read `file_path` from the sandbox and return numbered content."""
    if not isinstance(file_path, str) or not file_path.strip():
        return {
            "ok": False,
            "result": "Error: 'file_path' is required and must be a non-empty string.",
            "meta": {"tool": "file_read"},
        }

    try:
        content = await sandbox_service.read_file(sandbox_id, e2b_api_key, file_path)
    except SandboxError as exc:
        # Structured error returned to the LLM so the loop continues.
        return {
            "ok": False,
            "result": f"Error: could not read file '{file_path}'. It may not exist. Details: {exc}",
            "meta": {"tool": "file_read", "file_path": file_path},
        }

    numbered = _with_line_numbers(content)
    return {
        "ok": True,
        "result": numbered if numbered else "(file is empty)",
        "meta": {
            "tool": "file_read",
            "file_path": file_path,
            "lines": len(content.splitlines()),
        },
    }
