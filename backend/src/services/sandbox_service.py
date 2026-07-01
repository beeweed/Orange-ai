"""E2B Sandbox service.

Wraps the official E2B SDK to create, inspect, pause, resume, and reuse isolated
sandboxes, and to perform file read / write operations inside them. All blocking
SDK calls are executed in a thread pool so the asyncio event loop is never
blocked.

Design notes:
- A new sandbox is created lazily on a user's first message of a session.
- Sandboxes are keyed by their E2B sandbox id and cached in-process so the same
  session can reuse one sandbox across multiple agent turns.
- Timeout is set to 1 hour (configurable) as required.
- Sandboxes are configured to pause on timeout so they can be resumed later.
- Manual resume explicitly resets the timeout window back to the full configured
  duration.
"""
from __future__ import annotations

import asyncio
import base64
import json
import textwrap
from typing import Any, Dict, Optional

from e2b import Sandbox
from e2b.sandbox.sandbox_api import SandboxInfo

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SandboxError(Exception):
    """Raised when a sandbox operation fails."""


class SandboxPausedError(SandboxError):
    """Raised when a sandbox is paused and requires an explicit resume."""


class SandboxService:
    """Manages E2B sandbox lifecycle and file IO.

    Thread-safe for concurrent async access via an asyncio lock guarding the
    in-process cache. The E2B SDK itself is synchronous, so every call is
    offloaded with `asyncio.to_thread`.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._sandboxes: Dict[str, Sandbox] = {}
        self._paused_sandboxes: set[str] = set()
        self._lock = asyncio.Lock()

    def _timeout_seconds(self) -> int:
        return self._settings.sandbox_timeout_seconds

    def _lifecycle_config(self) -> dict:
        return {
            "on_timeout": "pause",
            "auto_resume": False,
        }

    async def _set_paused_state(self, sandbox_id: str, paused: bool) -> None:
        async with self._lock:
            if paused:
                self._paused_sandboxes.add(sandbox_id)
            else:
                self._paused_sandboxes.discard(sandbox_id)

    async def _cache_running_sandbox(self, sandbox: Sandbox) -> Sandbox:
        async with self._lock:
            self._sandboxes[sandbox.sandbox_id] = sandbox
            self._paused_sandboxes.discard(sandbox.sandbox_id)
        return sandbox

    async def create_sandbox(
        self,
        api_key: str,
        template: Optional[str] = None,
    ) -> str:
        """Create a new E2B sandbox and return its id."""
        timeout = self._timeout_seconds()
        lifecycle = self._lifecycle_config()

        def _create() -> Sandbox:
            return Sandbox.create(
                api_key=api_key,
                timeout=timeout,
                template=template,
                lifecycle=lifecycle,
            )

        try:
            sandbox = await asyncio.to_thread(_create)
        except Exception as exc:  # noqa: BLE001 - surface a clean error
            logger.error("Failed to create E2B sandbox: %s", exc)
            raise SandboxError(f"Failed to create sandbox: {exc}") from exc

        await self._cache_running_sandbox(sandbox)
        logger.info(
            "Created sandbox %s (timeout=%ss, template=%s, lifecycle=%s)",
            sandbox.sandbox_id,
            timeout,
            template or "default",
            lifecycle,
        )
        return sandbox.sandbox_id

    async def _connect_sandbox(
        self,
        sandbox_id: str,
        api_key: str,
        *,
        timeout: Optional[int] = None,
    ) -> Sandbox:
        """Connect to a sandbox and cache the running instance.

        If the sandbox is paused, E2B resumes it when connecting.
        """

        def _connect() -> Sandbox:
            return Sandbox.connect(sandbox_id, api_key=api_key, timeout=timeout)

        try:
            sandbox = await asyncio.to_thread(_connect)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to connect to sandbox %s: %s", sandbox_id, exc)
            raise SandboxError(f"Sandbox {sandbox_id} is not reachable: {exc}") from exc

        await self._cache_running_sandbox(sandbox)
        return sandbox

    async def _get_sandbox(self, sandbox_id: str, api_key: str) -> Sandbox:
        """Return a connected running sandbox instance.

        Paused sandboxes are intentionally not auto-resumed by file operations.
        They must be resumed explicitly through the resume API so the UI stays in
        sync with the user's chosen lifecycle action.
        """
        async with self._lock:
            if sandbox_id in self._paused_sandboxes:
                raise SandboxPausedError("Sandbox is paused. Resume it to continue.")
            cached = self._sandboxes.get(sandbox_id)
        if cached is not None:
            return cached

        return await self._connect_sandbox(sandbox_id, api_key)

    async def get_info(self, sandbox_id: str, api_key: str) -> SandboxInfo:
        """Fetch sandbox metadata without changing its lifecycle state."""

        def _get_info() -> SandboxInfo:
            return Sandbox.get_info(sandbox_id, api_key=api_key)

        try:
            info = await asyncio.to_thread(_get_info)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to inspect sandbox %s: %s", sandbox_id, exc)
            raise SandboxError(f"Sandbox {sandbox_id} is not reachable: {exc}") from exc

        await self._set_paused_state(sandbox_id, info.state.value == "paused")
        return info

    async def pause(self, sandbox_id: str, api_key: str) -> SandboxInfo:
        """Pause a sandbox while preserving memory and filesystem state."""

        def _pause() -> bool:
            return Sandbox.pause(sandbox_id, api_key=api_key, keep_memory=True)

        try:
            await asyncio.to_thread(_pause)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to pause sandbox %s: %s", sandbox_id, exc)
            raise SandboxError(f"Failed to pause sandbox {sandbox_id}: {exc}") from exc

        await self._set_paused_state(sandbox_id, True)
        logger.info("Paused sandbox %s", sandbox_id)
        return await self.get_info(sandbox_id, api_key)

    async def resume(self, sandbox_id: str, api_key: str) -> SandboxInfo:
        """Resume a sandbox and reset its timeout back to the full configured window."""
        timeout = self._timeout_seconds()
        sandbox = await self._connect_sandbox(sandbox_id, api_key, timeout=timeout)

        def _reset_timeout_and_get_info() -> SandboxInfo:
            # E2B connect() resumes the sandbox. We then call set_timeout() so the
            # new 1-hour window starts from the moment the user explicitly resumes.
            sandbox.set_timeout(timeout)
            return sandbox.get_info()

        try:
            info = await asyncio.to_thread(_reset_timeout_and_get_info)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to reset timeout for sandbox %s on resume: %s", sandbox_id, exc)
            raise SandboxError(f"Failed to resume sandbox {sandbox_id}: {exc}") from exc

        await self._cache_running_sandbox(sandbox)
        logger.info("Resumed sandbox %s and reset timeout to %ss", sandbox_id, timeout)
        return info

    async def write_file(
        self,
        sandbox_id: str,
        api_key: str,
        file_path: str,
        content: str,
    ) -> None:
        """Create or overwrite a file inside the sandbox filesystem."""
        sandbox = await self._get_sandbox(sandbox_id, api_key)

        def _write() -> None:
            sandbox.files.write(file_path, content)

        try:
            await asyncio.to_thread(_write)
        except Exception as exc:  # noqa: BLE001
            logger.error("write_file failed for %s: %s", file_path, exc)
            raise SandboxError(str(exc)) from exc
        logger.info("Wrote file %s (%d bytes) to sandbox %s", file_path, len(content), sandbox_id)

    async def read_file(
        self,
        sandbox_id: str,
        api_key: str,
        file_path: str,
    ) -> str:
        """Read a file's contents from the sandbox filesystem."""
        sandbox = await self._get_sandbox(sandbox_id, api_key)

        def _read() -> str:
            return sandbox.files.read(file_path)

        try:
            return await asyncio.to_thread(_read)
        except Exception as exc:  # noqa: BLE001
            logger.error("read_file failed for %s: %s", file_path, exc)
            raise SandboxError(str(exc)) from exc

    @staticmethod
    def _parse_command_json(stdout: str) -> Dict[str, Any]:
        """Extract the last JSON object emitted by a sandbox command."""
        for line in reversed((stdout or "").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise SandboxError("Sandbox command did not return a valid JSON payload.")

    async def run_command(
        self,
        sandbox_id: str,
        api_key: str,
        command: str,
        *,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Run a shell command inside the sandbox and return stdout/stderr metadata."""
        sandbox = await self._get_sandbox(sandbox_id, api_key)

        def _run() -> Dict[str, Any]:
            result = sandbox.commands.run(command, timeout=timeout)
            return {
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "exit_code": getattr(result, "exit_code", 0),
            }

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            logger.error("run_command failed: %s", exc)
            raise SandboxError(str(exc)) from exc

    async def insert_after_line(
        self,
        sandbox_id: str,
        api_key: str,
        *,
        file_path: str,
        line_number: int,
        content: str,
    ) -> Dict[str, Any]:
        """Insert content after a line by executing Python inside the sandbox."""
        payload_b64 = base64.b64encode(
            json.dumps(
                {
                    "file_path": file_path,
                    "line_number": line_number,
                    "content": content,
                }
            ).encode("utf-8")
        ).decode("ascii")

        command = textwrap.dedent(
            f"""\
            python - <<'PY'
            import base64
            import json
            import pathlib
            import re

            try:
                payload = json.loads(base64.b64decode({payload_b64!r}).decode("utf-8"))
                file_path = payload["file_path"]
                line_number = int(payload["line_number"])
                content = payload["content"]

                path = pathlib.Path(file_path)
                if not path.exists():
                    print(json.dumps({{"ok": False, "error": f"Error: file '{{file_path}}' does not exist.", "code": "FILE_NOT_FOUND"}}))
                    raise SystemExit(0)
                if not path.is_file():
                    print(json.dumps({{"ok": False, "error": f"Error: path '{{file_path}}' is not a file.", "code": "NOT_A_FILE"}}))
                    raise SystemExit(0)

                text = path.read_text(encoding="utf-8")
                lines = text.splitlines(keepends=True)
                if line_number < 1 or line_number > len(lines):
                    print(json.dumps({{
                        "ok": False,
                        "error": f"Error: 'line_number' must be between 1 and {{len(lines)}} for {{file_path}}.",
                        "code": "INVALID_LINE_NUMBER",
                        "line_count": len(lines),
                    }}))
                    raise SystemExit(0)

                newline_match = re.search(r"\\r\\n|\\n|\\r", text)
                newline = newline_match.group(0) if newline_match else "\\n"
                separator = "" if lines[line_number - 1].endswith(("\\n", "\\r")) else newline
                inserted = content
                if inserted and line_number < len(lines) and not inserted.endswith(("\\n", "\\r")):
                    inserted += newline

                updated = "".join(lines[:line_number]) + separator + inserted + "".join(lines[line_number:])
                path.write_text(updated, encoding="utf-8")
                print(json.dumps({{
                    "ok": True,
                    "line_count": len(lines),
                    "inserted_line_count": len(content.splitlines()) or (1 if content else 0),
                }}))
            except SystemExit:
                raise
            except Exception as exc:
                print(json.dumps({{"ok": False, "error": f"Error inserting content after line {{line_number}} in '{{file_path}}': {{exc}}", "code": "UNEXPECTED"}}))
            PY
            """
        )

        result = await self.run_command(sandbox_id, api_key, command, timeout=30)
        exit_code = result.get("exit_code")
        if exit_code not in (0, None):
            stderr = (result.get("stderr") or "").strip()
            stdout = (result.get("stdout") or "").strip()
            raise SandboxError(stderr or stdout or "insert_after_line command failed")
        return self._parse_command_json(result.get("stdout", ""))

    async def list_tree(self, sandbox_id: str, api_key: str, root: str = "/home/user") -> list[dict]:
        """List the recursive file tree under `root` for the explorer panel.

        Uses a shell `find` for portability and parses the flat path list into a
        structured node list the frontend can render as a tree.
        """
        sandbox = await self._get_sandbox(sandbox_id, api_key)

        def _list() -> list[dict]:
            # Exclude noisy/heavy directories from the explorer.
            cmd = (
                f"find {root} -not -path '*/node_modules/*' "
                f"-not -path '*/.git/*' -not -path '*/__pycache__/*' "
                f"-not -path '*/.next/*' -not -path '*/dist/*' "
                f"-printf '%y\\t%p\\n' 2>/dev/null | head -n 2000"
            )
            result = sandbox.commands.run(cmd, timeout=30)
            entries: list[dict] = []
            for line in (result.stdout or "").splitlines():
                if "\t" not in line:
                    continue
                kind, path = line.split("\t", 1)
                if path == root:
                    continue
                entries.append({
                    "path": path,
                    "type": "directory" if kind == "d" else "file",
                })
            return entries

        try:
            return await asyncio.to_thread(_list)
        except Exception as exc:  # noqa: BLE001
            logger.error("list_tree failed: %s", exc)
            return []

    async def kill(self, sandbox_id: str, api_key: str) -> None:
        """Terminate a sandbox and evict it from the cache."""

        def _kill() -> bool:
            return Sandbox.kill(sandbox_id, api_key=api_key)

        try:
            await asyncio.to_thread(_kill)
            logger.info("Killed sandbox %s", sandbox_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to kill sandbox %s: %s", sandbox_id, exc)
        finally:
            async with self._lock:
                self._sandboxes.pop(sandbox_id, None)
                self._paused_sandboxes.discard(sandbox_id)


# Module-level singleton used across the application.
sandbox_service = SandboxService()