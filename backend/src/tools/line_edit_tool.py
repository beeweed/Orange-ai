"""line_edit tool.

Replaces one line or an inclusive range of lines in an existing file inside the
active E2B sandbox. The caller must first inspect the file with ``file_read`` so
that the requested line numbers come from the latest numbered output.
"""
from __future__ import annotations

import re
from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService

LINE_EDIT_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "line_edit",
        "description": "Edit an existing file by replacing specific line(s). Use this tool when a string replacement is ambiguous because there are multiple matches, or when you want to update a specific section of a file. single line number (e.g. `27`) to replace one line. Use an inclusive range (e.g. `25-37`) to replace multiple consecutive lines. from the latest Read output.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path of the file to modify.",
                },
                "old_string_line_numbers": {
                    "type": "string",
                    "description": "single line number (e.g. `27`) to replace one line. Use an inclusive range (e.g. `25-37`) to replace multiple consecutive lines.",
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement content. string, code block, anything.",
                },
            },
            "required": ["file_path", "old_string_line_numbers", "new_string"],
        },
    },
}

_LINE_SPEC_RE = re.compile(r"^(?P<start>[1-9]\d*)(?:-(?P<end>[1-9]\d*))?$")


def _parse_line_spec(raw: str) -> tuple[int, int] | None:
    match = _LINE_SPEC_RE.fullmatch((raw or "").strip())
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        return None
    return start, end


def _detect_newline(text: str) -> str:
    for candidate in ("\r\n", "\n", "\r"):
        if candidate in text:
            return candidate
    return "\n"


async def line_edit(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    file_path: str,
    old_string_line_numbers: str,
    new_string: str,
    execution_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Replace specific line(s) in an existing sandbox file."""
    execution_context = execution_context or {}
    read_files = execution_context.get("read_files", set())

    if not isinstance(file_path, str) or not file_path.strip():
        return {
            "ok": False,
            "result": "Error: 'file_path' is required and must be a non-empty string.",
            "meta": {"tool": "line_edit"},
        }
    if not file_path.startswith("/"):
        return {
            "ok": False,
            "result": "Error: 'file_path' must be an absolute path.",
            "meta": {"tool": "line_edit", "file_path": file_path},
        }
    if not isinstance(old_string_line_numbers, str) or not old_string_line_numbers.strip():
        return {
            "ok": False,
            "result": "Error: 'old_string_line_numbers' is required and must be a non-empty string.",
            "meta": {"tool": "line_edit", "file_path": file_path},
        }
    if not isinstance(new_string, str):
        return {
            "ok": False,
            "result": "Error: 'new_string' must be a string.",
            "meta": {"tool": "line_edit", "file_path": file_path},
        }
    if file_path not in read_files:
        return {
            "ok": False,
            "result": (
                "Error: you must call file_read on this file before using line_edit. "
                "The line numbers must come from the latest file_read output in the current turn."
            ),
            "meta": {"tool": "line_edit", "file_path": file_path, "requires_read": True},
        }

    parsed = _parse_line_spec(old_string_line_numbers)
    if parsed is None:
        return {
            "ok": False,
            "result": (
                "Error: 'old_string_line_numbers' must be a single line number like '27' "
                "or an inclusive range like '25-37'."
            ),
            "meta": {
                "tool": "line_edit",
                "file_path": file_path,
                "old_string_line_numbers": old_string_line_numbers,
                "code": "INVALID_LINE_RANGE",
            },
        }
    start_line, end_line = parsed

    try:
        content = await sandbox_service.read_file(sandbox_id, e2b_api_key, file_path)
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error: file '{file_path}' does not exist or could not be read. Details: {exc}",
            "meta": {"tool": "line_edit", "file_path": file_path, "code": "FILE_NOT_FOUND"},
        }

    lines = content.splitlines()
    line_count = len(lines)
    if start_line < 1 or end_line > line_count:
        return {
            "ok": False,
            "result": (
                f"Error: old_string_line_numbers '{old_string_line_numbers}' was not found in {file_path}. "
                f"Valid lines are 1-{line_count}."
            ),
            "meta": {
                "tool": "line_edit",
                "file_path": file_path,
                "old_string_line_numbers": old_string_line_numbers,
                "line_count": line_count,
                "code": "LINE_RANGE_NOT_FOUND",
            },
        }

    newline = _detect_newline(content)
    replacement_lines = new_string.splitlines() if new_string else []
    updated_lines = lines[: start_line - 1] + replacement_lines + lines[end_line:]
    updated_content = newline.join(updated_lines)
    if content.endswith(("\r\n", "\n", "\r")) and updated_lines:
        updated_content += newline

    try:
        await sandbox_service.write_file(sandbox_id, e2b_api_key, file_path, updated_content)
    except SandboxError as exc:
        return {
            "ok": False,
            "result": f"Error writing updated file '{file_path}': {exc}",
            "meta": {"tool": "line_edit", "file_path": file_path},
        }

    return {
        "ok": True,
        "result": (
            f"Successfully replaced line(s) {old_string_line_numbers} in {file_path}."
        ),
        "meta": {
            "tool": "line_edit",
            "file_path": file_path,
            "old_string_line_numbers": old_string_line_numbers,
            "start_line": start_line,
            "end_line": end_line,
            "replaced_line_count": (end_line - start_line) + 1,
            "new_line_count": len(replacement_lines),
        },
    }