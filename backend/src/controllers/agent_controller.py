"""Agent controller.

Bridges the HTTP layer and the agent loop. Responsibilities:
- Ensure a sandbox exists (create on first message, emitting sandbox events).
- Drive the agent and translate its structured events into SSE frames.
- Periodically refresh and emit the sandbox file tree so the explorer updates.
- Centralised error handling so failures are surfaced, never silent.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List

from src.agent.agent import Agent
from src.config.settings import get_settings
from src.schemas.chat import ChatRequest
from src.services.sandbox_service import SandboxError, sandbox_service
from src.utils.logger import get_logger
from src.utils.sse import sse_comment, sse_event

logger = get_logger(__name__)


class AgentController:
    """Orchestrates a single streaming agent request."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._agent = Agent(max_iterations=self._settings.max_iterations)

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Yield SSE-encoded frames for one chat request."""
        creds = request.credentials

        # ---- 1. Ensure a sandbox exists ---- #
        sandbox_id = request.sandbox_id
        try:
            if not sandbox_id:
                yield sse_event("sandbox_creating")
                sandbox_id = await sandbox_service.create_sandbox(
                    api_key=creds.e2b_api_key,
                    template=creds.sandbox_template,
                )
                yield sse_event("sandbox_created", {"sandbox_id": sandbox_id})
            else:
                info = await sandbox_service.get_info(sandbox_id, creds.e2b_api_key)
                if info.state.value == "paused":
                    yield sse_event("error", {"message": "Sandbox is paused. Resume it to continue."})
                    yield sse_event("done", {"iterations": 0})
                    return
                yield sse_event("sandbox_ready", {"sandbox_id": sandbox_id})
        except SandboxError as exc:
            yield sse_event("error", {"message": f"Sandbox initialisation failed: {exc}"})
            yield sse_event("done", {"iterations": 0})
            return

        # Convert validated history models into provider dicts.
        history: List[Dict[str, Any]] = [m.to_provider_dict() for m in request.history]

        # ---- 2. Drive the agent loop ---- #
        files_dirty = False
        try:
            async for evt in self._agent.run(
                credentials=creds,
                history=history,
                user_message=request.message,
                sandbox_id=sandbox_id,
            ):
                etype = evt.get("type")

                # Mark the tree dirty after a successful file mutation so we refresh it.
                if etype == "tool_result" and evt.get("ok") and evt.get("name") in {"file_write", "file_editor", "line_edit", "insert_after_line"}:
                    files_dirty = True

                yield sse_event(etype, {k: v for k, v in evt.items() if k != "type"})

                # After a write completes, push an updated file tree.
                if etype == "tool_result" and files_dirty:
                    files_dirty = False
                    tree = await sandbox_service.list_tree(sandbox_id, creds.e2b_api_key)
                    yield sse_event("file_tree", {"sandbox_id": sandbox_id, "files": tree})

                # Heartbeat to keep intermediaries from buffering/closing.
                await asyncio.sleep(0)
        except Exception as exc:  # noqa: BLE001 - guarantee a clean stream close
            logger.exception("Agent stream crashed")
            yield sse_event("error", {"message": f"Internal agent error: {exc}"})
            yield sse_event("done", {"iterations": 0})
            return

        # Final tree snapshot at the end of the turn.
        try:
            tree = await sandbox_service.list_tree(sandbox_id, creds.e2b_api_key)
            yield sse_event("file_tree", {"sandbox_id": sandbox_id, "files": tree})
        except Exception:  # noqa: BLE001
            pass

        yield sse_comment("stream-complete")


agent_controller = AgentController()
