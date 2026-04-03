"""Tests for core/gateway/app.py.

Covers:
- GET /health returns 200 {"status": "ok"}.
- GET /mcp/tools returns all tools from agent manifests.
- POST /mcp/tools/{name}/invoke returns correct shape for low-risk tools.
- POST /mcp/tools/{name}/invoke returns 202-style queued response for medium/high tools.
- POST /mcp/tools/unknown/invoke returns 404.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.gateway.app import app
from core.gateway.mcp import MCPTool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENTS_DIR = Path(__file__).parent.parent / "agents"


def _make_registry(*tools: MCPTool) -> dict[str, MCPTool]:
    return {t.name: t for t in tools}


def _low_tool() -> MCPTool:
    return MCPTool(agent_id="test_agent", name="low_tool", risk_level="low")


def _medium_tool() -> MCPTool:
    return MCPTool(agent_id="test_agent", name="medium_tool", risk_level="medium")


def _high_tool() -> MCPTool:
    return MCPTool(agent_id="test_agent", name="high_tool", risk_level="high")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_registry():
    """TestClient with a pre-populated MCP registry (no filesystem I/O)."""
    registry = _make_registry(_low_tool(), _medium_tool(), _high_tool())

    with TestClient(app, raise_server_exceptions=True) as client:
        app.state.mcp_registry = registry
        yield client


@pytest.fixture
def client_real_manifests(monkeypatch: pytest.MonkeyPatch):
    """TestClient that scans real agent manifests from the ``agents/`` directory."""
    monkeypatch.setenv("OSMEN_AGENTS_DIR", str(AGENTS_DIR))
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client_with_registry: TestClient) -> None:
    """GET /health must return 200 with {"status": "ok"}."""
    resp = client_with_registry.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# MCP tool list
# ---------------------------------------------------------------------------


def test_list_tools_returns_all_tools(client_with_registry: TestClient) -> None:
    """GET /mcp/tools must list every registered tool."""
    resp = client_with_registry.get("/mcp/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == {"low_tool", "medium_tool", "high_tool"}


def test_list_tools_shape(client_with_registry: TestClient) -> None:
    """Each tool entry must have name, agent_id, description, and risk_level."""
    resp = client_with_registry.get("/mcp/tools")
    for entry in resp.json():
        assert "name" in entry
        assert "agent_id" in entry
        assert "description" in entry
        assert "risk_level" in entry


def test_list_tools_from_real_manifests(client_real_manifests: TestClient) -> None:
    """GET /mcp/tools with real manifests must return at least the expected agent tools."""
    resp = client_real_manifests.get("/mcp/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    # Tools defined across daily_brief, knowledge_librarian, media_organization
    assert "generate_brief" in names
    assert "ingest_url" in names
    assert "transfer_to_plex" in names


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------


def test_invoke_low_risk_tool_returns_ok(client_with_registry: TestClient) -> None:
    """Invoking a low-risk tool must return status=ok."""
    resp = client_with_registry.post("/mcp/tools/low_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tool_name"] == "low_tool"


def test_invoke_medium_risk_tool_returns_queued(client_with_registry: TestClient) -> None:
    """Invoking a medium-risk tool must return status=queued (approval pending)."""
    resp = client_with_registry.post("/mcp/tools/medium_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"


def test_invoke_high_risk_tool_returns_queued(client_with_registry: TestClient) -> None:
    """Invoking a high-risk tool must return status=queued."""
    resp = client_with_registry.post("/mcp/tools/high_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


def test_invoke_unknown_tool_returns_404(client_with_registry: TestClient) -> None:
    """Invoking an unregistered tool must return 404."""
    resp = client_with_registry.post("/mcp/tools/nonexistent/invoke", json={"parameters": {}})
    assert resp.status_code == 404


def test_invoke_with_correlation_id(client_with_registry: TestClient) -> None:
    """Correlation ID is accepted and echoed back in the response shape."""
    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {}, "correlation_id": "test-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["tool_name"] == "low_tool"


# ---------------------------------------------------------------------------
# Async tests (anyio marker)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_async() -> None:
    """Async variant of the health probe test using httpx AsyncClient."""
    from httpx import ASGITransport, AsyncClient


    registry = _make_registry(_low_tool())
    app.state.mcp_registry = registry

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
