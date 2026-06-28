"""E2B Sandbox service.

Wraps the official E2B SDK to create and reuse isolated sandboxes, and to
perform file read / write operations inside them. All blocking SDK calls are
executed in a thread pool so the asyncio event loop is never blocked.

Design notes:
- A new sandbox is created lazily on a user's first message of a session.
- Sandboxes are keyed by their E2B sandbox id and cached in-process so the same
  session can reuse one sandbox across multiple agent turns.
- Timeout is set to 1 hour (configurable) as required.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from e2b import Sandbox

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SandboxError(Exception):
    """Raised when a sandbox operation fails."""


class SandboxService:
    """Manages E2B sandbox lifecycle and file IO.

    Thread-safe for concurrent async access via an asyncio lock guarding the
    in-process cache. The E2B SDK itself is synchronous, so every call is
    offloaded with `asyncio.to_thread`.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._sandboxes: Dict[str, Sandbox] = {}
        self._lock = asyncio.Lock()

    async def create_sandbox(
        self,
        api_key: str,
        template: Optional[str] = None,
    ) -> str:
        """Create a new E2B sandbox and return its id."""
        timeout = self._settings.sandbox_timeout_seconds

        def _create() -> Sandbox:
            return Sandbox.create(
                api_key=api_key,
                timeout=timeout,
                template=template,
            )

        try:
            sandbox = await asyncio.to_thread(_create)
        except Exception as exc:  # noqa: BLE001 - surface a clean error
            logger.error("Failed to create E2B sandbox: %s", exc)
            raise SandboxError(f"Failed to create sandbox: {exc}") from exc

        sandbox_id = sandbox.sandbox_id
        async with self._lock:
            self._sandboxes[sandbox_id] = sandbox
        logger.info("Created sandbox %s (timeout=%ss, template=%s)", sandbox_id, timeout, template or "default")
        return sandbox_id

    async def _get_sandbox(self, sandbox_id: str, api_key: str) -> Sandbox:
        """Return a connected sandbox, reconnecting from cache or by id."""
        async with self._lock:
            cached = self._sandboxes.get(sandbox_id)
        if cached is not None:
            return cached

        # Reconnect to an existing running sandbox (e.g. after process restart).
        def _connect() -> Sandbox:
            return Sandbox.connect(sandbox_id, api_key=api_key)

        try:
            sandbox = await asyncio.to_thread(_connect)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to connect to sandbox %s: %s", sandbox_id, exc)
            raise SandboxError(f"Sandbox {sandbox_id} is not reachable: {exc}") from exc

        async with self._lock:
            self._sandboxes[sandbox_id] = sandbox
        return sandbox

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
        async with self._lock:
            sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox is None:
            return

        def _kill() -> None:
            sandbox.kill()

        try:
            await asyncio.to_thread(_kill)
            logger.info("Killed sandbox %s", sandbox_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to kill sandbox %s: %s", sandbox_id, exc)


# Module-level singleton used across the application.
sandbox_service = SandboxService()
