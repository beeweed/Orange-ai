"""file_editor tool.

Performs exact string replacement in an existing file inside the E2B sandbox.
The tool is intentionally strict so the agent must inspect the file first and
make targeted, reviewable edits instead of blindly overwriting content.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from src.services.sandbox_service import SandboxError, SandboxService

FILE_EDITOR_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "file_editor",
        "description": "Performs exact string replacements in files.\n\nUsage:\n- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file\n- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string\n- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required\n- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked\n- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`\n- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurences of old_string (default false)",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
}


def _has_been_read(file_path: str, read_files: Iterable[str] | None) -> bool:
    if not read_files:
        return False
    return file_path in set(read_files)


async def file_editor(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    read_files: Iterable[str] | None,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> Dict[str, Any]:
    """Perform exact string replacement in an existing sandbox file."""
    if not isinstance(file_path, str) or not file_path.strip():
        return {
            "ok": False,
            "result": "Error: 'file_path' is required and must be a non-empty string.",
            "meta": {"tool": "file_editor"},
        }
    if not file_path.startswith("/"):
        return {
            "ok": False,
            "result": "Error: 'file_path' must be an absolute path.",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if not isinstance(old_string, str) or old_string == "":
        return {
            "ok": False,
            "result": "Error: 'old_string' is required and must be a non-empty string.",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if not isinstance(new_string, str):
        return {
            "ok": False,
            "result": "Error: 'new_string' must be a string.",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if new_string == old_string:
        return {
            "ok": False,
            "result": "Error: 'new_string' must be different from 'old_string'.",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if not isinstance(replace_all, bool):
        return {
            "ok": False,
            "result": "Error: 'replace_all' must be a boolean when provided.",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if not _has_been_read(file_path, read_files):
        return {
            "ok": False,
            "result": (
                "Error: file_editor requires the agent to read this file first in the current turn. "
                "Call file_read with the same 'file_path', inspect the numbered output, then retry file_editor."
            ),
            "meta": {"tool": "file_editor", "file_path": file_path, "needs_read": True},
        }

    try:
        content = await sandbox_service.read_file(sandbox_id, e2b_api_key, file_path)
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error: file '{file_path}' does not exist or could not be read. Details: {exc}",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }

    matches = content.count(old_string)
    if matches == 0:
        return {
            "ok": False,
            "result": (
                "Error: 'old_string' was not found in the file. "
                "Read the file again and ensure the text matches exactly, including whitespace."
            ),
            "meta": {"tool": "file_editor", "file_path": file_path},
        }
    if matches > 1 and not replace_all:
        return {
            "ok": False,
            "result": (
                "Error: multiple matches found for 'old_string'. "
                "Provide a more specific unique string or set 'replace_all' to true."
            ),
            "meta": {
                "tool": "file_editor",
                "file_path": file_path,
                "matches": matches,
                "requires_replace_all": True,
            },
        }

    updated = content.replace(old_string, new_string, matches if replace_all else 1)

    try:
        await sandbox_service.write_file(sandbox_id, e2b_api_key, file_path, updated)
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error writing updated file '{file_path}': {exc}",
            "meta": {"tool": "file_editor", "file_path": file_path},
        }

    return {
        "ok": True,
        "result": (
            f"Successfully replaced {matches if replace_all else 1} occurrence(s) in {file_path}."
        ),
        "meta": {
            "tool": "file_editor",
            "file_path": file_path,
            "replacements": matches if replace_all else 1,
            "replace_all": replace_all,
        },
    }