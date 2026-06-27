"""Integration test for the agent loop with mocked LLM + sandbox.

Validates the full Plan -> Act -> Observe -> Reflect cycle:
- The agent streams content tokens.
- A native tool call is executed against a stubbed sandbox.
- The tool result is fed back and a final assistant message is produced.
- Iteration accounting and terminal events are emitted correctly.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List

import pytest

import src.agent.agent as agent_module
from src.agent.agent import Agent
from src.schemas.chat import Credentials, Provider


class _FakeLLM:
    """Scripted two-turn LLM: first requests a tool, then finishes."""

    def __init__(self) -> None:
        self.turn = 0

    async def stream_chat(
        self, *, provider, api_key, model, messages, tools
    ) -> AsyncGenerator[Dict[str, Any], None]:
        self.turn += 1
        if self.turn == 1:
            # Stream some thinking content, then a file_write tool call.
            for piece in ["Creating ", "the ", "file."]:
                yield {"kind": "content", "text": piece}
            yield {
                "kind": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "file_write",
                            "arguments": '{"file_path": "/home/user/app.py", "content": "print(1)"}',
                        },
                    }
                ],
            }
            yield {"kind": "finish", "reason": "tool_calls"}
        else:
            for piece in ["Done. ", "File written."]:
                yield {"kind": "content", "text": piece}
            yield {"kind": "finish", "reason": "stop"}


class _FakeSandbox:
    def __init__(self) -> None:
        self.store: Dict[str, str] = {}

    async def write_file(self, sandbox_id, api_key, file_path, content):
        self.store[file_path] = content

    async def read_file(self, sandbox_id, api_key, file_path):
        return self.store[file_path]


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    fake_llm = _FakeLLM()
    fake_sb = _FakeSandbox()
    monkeypatch.setattr(agent_module.llm_service, "stream_chat", fake_llm.stream_chat)
    # Patch the sandbox service used by the tools registry.
    import src.tools as tools_mod
    monkeypatch.setattr(tools_mod, "sandbox_service", fake_sb)
    # file_write/file_read receive sandbox_service as first arg from execute_tool,
    # which references the module-level singleton; patch that too.
    import src.tools.file_write  # noqa: F401
    import src.tools.file_read  # noqa: F401
    return fake_sb


def test_agent_full_cycle(_patch):
    agent = Agent(max_iterations=1000)

    async def _run() -> List[Dict[str, Any]]:
        creds = Credentials(
            provider=Provider.OPENROUTER,
            api_key="k",
            model="m",
            e2b_api_key="e",
        )
        events: List[Dict[str, Any]] = []
        async for evt in agent.run(
            credentials=creds,
            history=[],
            user_message="make app.py",
            sandbox_id="sb_1",
        ):
            events.append(evt)
        return events

    events = asyncio.run(_run())
    types = [e["type"] for e in events]

    # Tokens were streamed.
    assert types.count("token") >= 3
    # A tool call and result were produced.
    assert "tool_call" in types
    tool_results = [e for e in events if e["type"] == "tool_result"]
    assert tool_results and tool_results[0]["ok"] is True
    # The file was actually written to the stubbed sandbox.
    assert _patch.store["/home/user/app.py"] == "print(1)"
    # Two iterations occurred (tool turn + final turn).
    iters = [e for e in events if e["type"] == "iteration"]
    assert len(iters) == 2
    # Terminal done event present.
    assert types[-1] == "done"
