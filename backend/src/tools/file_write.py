"""file_write tool.

Creates or fully overwrites a file at an absolute path inside the E2B sandbox.
No size or type limits are imposed by this tool.
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.sandbox_service import SandboxError, SandboxService
from src.tools.schemas import FileWriteParams, pydantic_to_openai_schema
from src.utils.logger import get_logger

logger = get_logger(__name__)

FILE_WRITE_SCHEMA: Dict[str, Any] = pydantic_to_openai_schema(
    name="file_write",
    description="Create or overwrite a file at the given path inside the sandbox. Use for creating new files or fully rewriting existing ones.",
    params_model=FileWriteParams,
)


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
    try:
        FileWriteParams(file_path=file_path, content=content)
    except Exception as exc:
        return {
            "ok": False,
            "result": f"Error: invalid parameters: {exc}",
            "meta": {"tool": "file_write"},
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
