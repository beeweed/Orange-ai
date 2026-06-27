"""Unit tests for the tool layer.

These tests validate tool schemas, argument validation, and the agent's
JSON-argument parsing / repeat-detection helpers without requiring a live
sandbox or LLM provider (the sandbox service is stubbed).
"""
from __future__ import annotations

import asyncio

import pytest

from src.agent.agent import Agent
from src.tools import TOOL_SCHEMAS, execute_tool
from src.tools.file_read import FILE_READ_SCHEMA, file_read
from src.tools.file_write import FILE_WRITE_SCHEMA, file_write


class _StubSandbox:
    """In-memory stub mirroring SandboxService's IO surface."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def write_file(self, sandbox_id, api_key, file_path, content):
        self.store[file_path] = content

    async def read_file(self, sandbox_id, api_key, file_path):
        from src.services.sandbox_service import SandboxError

        if file_path not in self.store:
            raise SandboxError("not found")
        return self.store[file_path]


def test_tool_schemas_present():
    names = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert names == {"file_write", "file_read"}


def test_file_write_schema_shape():
    fn = FILE_WRITE_SCHEMA["function"]
    assert fn["name"] == "file_write"
    assert set(fn["parameters"]["required"]) == {"file_path", "content"}


def test_file_read_schema_shape():
    fn = FILE_READ_SCHEMA["function"]
    assert fn["name"] == "file_read"
    assert fn["parameters"]["required"] == ["file_path"]


def test_write_then_read_roundtrip():
    stub = _StubSandbox()

    async def _run():
        w = await file_write(
            stub, sandbox_id="sb", e2b_api_key="k",
            file_path="/home/user/a.txt", content="hello\nworld",
        )
        assert w["ok"] is True
        r = await file_read(
            stub, sandbox_id="sb", e2b_api_key="k", file_path="/home/user/a.txt",
        )
        assert r["ok"] is True
        assert "1\thello" in r["result"]
        assert "2\tworld" in r["result"]

    asyncio.run(_run())


def test_read_missing_returns_structured_error():
    stub = _StubSandbox()

    async def _run():
        r = await file_read(
            stub, sandbox_id="sb", e2b_api_key="k", file_path="/home/user/missing.txt",
        )
        assert r["ok"] is False
        assert "could not read" in r["result"].lower()

    asyncio.run(_run())


def test_parse_arguments_valid_and_recovery():
    assert Agent._parse_arguments('{"a": 1}') == {"a": 1}
    # Recovery from surrounding noise.
    assert Agent._parse_arguments('prefix {"b": 2} suffix') == {"b": 2}
    assert Agent._parse_arguments("") == {}


def test_signature_stability():
    s1 = Agent._signature("file_write", {"file_path": "/x", "content": "y"})
    s2 = Agent._signature("file_write", {"content": "y", "file_path": "/x"})
    assert s1 == s2
