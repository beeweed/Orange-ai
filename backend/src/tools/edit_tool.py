"""file_editor tool.

Performs exact string replacement in an existing file inside the E2B sandbox.
The tool is intentionally strict so the agent must inspect the file first and
make targeted, reviewable edits instead of blindly overwriting content.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService
from src.tools.schemas import FileEditorParams, pydantic_to_openai_schema

FILE_EDITOR_SCHEMA: Dict[str, Any] = pydantic_to_openai_schema(
    name="file_editor",
    description="Performs exact string replacements in files.\n\nUsage:\n- When editing text, ensure you preserve the exact indentation (tabs/spaces) as it appears in the file.\n- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.\n- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.\n- The edit will FAIL if `old_string` is not found in the file. Provide exact matching text including whitespace.\n- If `old_string` matches multiple times and `replace_all` is false, provide more context to make it unique, or set `replace_all` to true.\n- Use `replace_all` to rename all occurrences of a string across the file.",
    params_model=FileEditorParams,
)


async def file_editor(
    sandbox_service: SandboxService,
    *,
    sandbox_id: str,
    e2b_api_key: str,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> Dict[str, Any]:
    """Perform exact string replacement in an existing sandbox file.

    The tool reads the file directly from the sandbox, so prior file_read is
    not required. Always matches against raw file content.
    """
    try:
        FileEditorParams(file_path=file_path, old_string=old_string, new_string=new_string, replace_all=replace_all)
    except Exception as exc:
        return {
            "ok": False,
            "result": f"Error: invalid parameters: {exc}",
            "meta": {"tool": "file_editor"},
        }
    if new_string == old_string:
        return {
            "ok": False,
            "result": "Error: 'new_string' must be different from 'old_string'.",
            "meta": {"tool": "file_editor", "file_path": file_path},
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
                "Ensure the text matches exactly, including whitespace, quotes, and special characters. "
                "If your string contains quotes or escaped characters, verify they match "
                "the raw file content exactly."
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