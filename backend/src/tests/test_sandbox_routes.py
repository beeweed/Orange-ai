"""Route tests for sandbox lifecycle controls.

These tests validate the new pause/resume/status endpoints without requiring a
live E2B account by monkeypatching the sandbox service used by the routes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.main import create_app
from src.api import routes as routes_module


class _StubSandboxService:
    def __init__(self) -> None:
        self.end_at = datetime.now(timezone.utc) + timedelta(hours=1)

    async def get_info(self, sandbox_id: str, api_key: str):
        return SimpleNamespace(
            sandbox_id=sandbox_id,
            state=SimpleNamespace(value="running"),
            end_at=self.end_at,
        )

    async def pause(self, sandbox_id: str, api_key: str):
        return SimpleNamespace(
            sandbox_id=sandbox_id,
            state=SimpleNamespace(value="paused"),
            end_at=self.end_at,
        )

    async def resume(self, sandbox_id: str, api_key: str):
        return SimpleNamespace(
            sandbox_id=sandbox_id,
            state=SimpleNamespace(value="running"),
            end_at=self.end_at,
        )


def test_sandbox_status_route(monkeypatch):
    monkeypatch.setattr(routes_module, "sandbox_service", _StubSandboxService())
    client = TestClient(create_app())

    resp = client.post(
        "/api/sandbox/status",
        json={"sandbox_id": "sbx_123", "e2b_api_key": "e2b_test"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["sandbox_id"] == "sbx_123"
    assert body["state"] == "running"
    assert body["timeout_seconds"] == 3600
    assert body["end_at"].endswith("+00:00")


def test_sandbox_pause_route(monkeypatch):
    monkeypatch.setattr(routes_module, "sandbox_service", _StubSandboxService())
    client = TestClient(create_app())

    resp = client.post(
        "/api/sandbox/pause",
        json={"sandbox_id": "sbx_123", "e2b_api_key": "e2b_test"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["sandbox_id"] == "sbx_123"
    assert body["state"] == "paused"
    assert body["status"] == "paused"


def test_sandbox_resume_route(monkeypatch):
    monkeypatch.setattr(routes_module, "sandbox_service", _StubSandboxService())
    client = TestClient(create_app())

    resp = client.post(
        "/api/sandbox/resume",
        json={"sandbox_id": "sbx_123", "e2b_api_key": "e2b_test"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["sandbox_id"] == "sbx_123"
    assert body["state"] == "running"
    assert body["status"] == "running"
    assert body["timeout_seconds"] == 3600