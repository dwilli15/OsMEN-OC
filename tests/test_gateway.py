"""Tests for core/gateway/app.py.

Covers:
- GET /health returns 200 {"status": "ok"}.
- GET /mcp/tools returns all tools from agent manifests.
- POST /mcp/tools/{name}/invoke — approved path (low risk → status="ok").
- POST /mcp/tools/{name}/invoke — queued path (medium risk → status="queued").
- POST /mcp/tools/{name}/invoke — denied path (high risk, no callback → 403).
- POST /mcp/tools/{name}/invoke — audit failure → 500 structured error.
- POST /mcp/tools/{name}/invoke — approval gate failure → 500 structured error.
- POST /mcp/tools/{name}/invoke — handler failure → 500 structured error.
- POST /mcp/tools/unknown/invoke returns 404.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.gateway.app import _resolve_database_url, app
from core.gateway.deps import get_approval_gate, get_audit_trail, get_event_bus
from core.gateway.mcp import MCPTool
from core.utils.exceptions import ApprovalError, AuditError, EventBusError

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


def _mock_trail(*, insert_side_effect=None) -> AsyncMock:
    """Return an AsyncMock AuditTrail with a configurable insert side effect."""
    trail = AsyncMock()
    if insert_side_effect is not None:
        trail.insert = AsyncMock(side_effect=insert_side_effect)
    else:
        trail.insert = AsyncMock(return_value="audit-id-123")
    return trail


def _mock_bus(*, publish_side_effect=None) -> AsyncMock:
    """Return an AsyncMock EventBus with a configurable publish side effect."""
    bus = AsyncMock()
    if publish_side_effect is not None:
        bus.publish = AsyncMock(side_effect=publish_side_effect)
    else:
        bus.publish = AsyncMock(return_value="1-0")
    return bus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_registry():
    """TestClient with a pre-populated MCP registry and mocked AuditTrail.

    The ApprovalGate is *not* overridden — the default (no callback) instance
    is used, which auto-approves low/medium and denies high/critical.
    """
    registry = _make_registry(_low_tool(), _medium_tool(), _high_tool())
    trail = _mock_trail()
    bus = _mock_bus()
    app.dependency_overrides[get_audit_trail] = lambda: trail
    app.dependency_overrides[get_event_bus] = lambda: bus

    with TestClient(app, raise_server_exceptions=True) as client:
        app.state.mcp_registry = registry
        yield client

    app.dependency_overrides.pop(get_audit_trail, None)
    app.dependency_overrides.pop(get_event_bus, None)


@pytest.fixture
def client_real_manifests(monkeypatch: pytest.MonkeyPatch):
    """TestClient that scans real agent manifests from the ``agents/`` directory."""
    monkeypatch.setenv("OSMEN_AGENTS_DIR", str(AGENTS_DIR))
    trail = _mock_trail()
    bus = _mock_bus()
    app.dependency_overrides[get_audit_trail] = lambda: trail
    app.dependency_overrides[get_event_bus] = lambda: bus

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    app.dependency_overrides.pop(get_audit_trail, None)
    app.dependency_overrides.pop(get_event_bus, None)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client_with_registry: TestClient) -> None:
    """GET /health must return 200 with {"status": "ok"}."""
    resp = client_with_registry.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readiness_returns_status(client_with_registry: TestClient) -> None:
    """GET /ready returns 200 with a status field and dependency checks."""
    resp = client_with_registry.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ready", "degraded")
    assert "checks" in body
    assert "redis" in body["checks"]
    assert "postgres" in body["checks"]
    assert "bridge" in body["checks"]


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
# Tool invocation — approved paths
# ---------------------------------------------------------------------------


def test_invoke_low_risk_tool_returns_ok(client_with_registry: TestClient) -> None:
    """Invoking a low-risk tool must return status=ok (auto-approved, not flagged)."""
    resp = client_with_registry.post("/mcp/tools/low_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tool_name"] == "low_tool"


def test_invoke_medium_risk_tool_returns_queued(client_with_registry: TestClient) -> None:
    """Invoking a medium-risk tool must return status=queued (approved, flagged for summary)."""
    resp = client_with_registry.post("/mcp/tools/medium_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"


def test_invoke_approved_calls_audit_trail(client_with_registry: TestClient) -> None:
    """Invoking an approved tool must write exactly one AuditRecord via the trail."""
    trail = _mock_trail()
    app.dependency_overrides[get_audit_trail] = lambda: trail

    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {"key": "val"}, "correlation_id": "cid-001"},
    )
    assert resp.status_code == 200
    trail.insert.assert_called_once()
    record = trail.insert.call_args[0][0]
    assert record.tool_name == "low_tool"
    assert record.outcome == "approved"
    assert record.correlation_id == "cid-001"


def test_invoke_with_correlation_id(client_with_registry: TestClient) -> None:
    """Correlation ID is accepted and the response shape is correct."""
    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {}, "correlation_id": "test-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["tool_name"] == "low_tool"


def test_invoke_approved_publishes_event(client_with_registry: TestClient) -> None:
    """Approved invocations must publish one EventEnvelope to the event bus."""
    bus = _mock_bus()
    app.dependency_overrides[get_event_bus] = lambda: bus

    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {"x": 1}, "correlation_id": "cid-evt"},
    )
    assert resp.status_code == 200
    bus.publish.assert_called_once()
    envelope = bus.publish.call_args[0][0]
    assert envelope.domain == "tools"
    assert envelope.category == "invocation"
    assert envelope.payload["tool_name"] == "low_tool"
    assert envelope.payload["agent_id"] == "test_agent"
    assert envelope.payload["risk_level"] == "low"
    assert envelope.payload["outcome"] == "approved"
    assert envelope.payload["correlation_id"] == "cid-evt"


# ---------------------------------------------------------------------------
# Tool invocation — denied path
# ---------------------------------------------------------------------------


def test_invoke_high_risk_tool_returns_403(client_with_registry: TestClient) -> None:
    """Invoking a high-risk tool without an approval callback must return 403."""
    resp = client_with_registry.post("/mcp/tools/high_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "tool_denied"


def test_invoke_denied_writes_audit_record(client_with_registry: TestClient) -> None:
    """A denied invocation must still write an AuditRecord with outcome=denied."""
    trail = _mock_trail()
    app.dependency_overrides[get_audit_trail] = lambda: trail

    resp = client_with_registry.post("/mcp/tools/high_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 403
    trail.insert.assert_called_once()
    record = trail.insert.call_args[0][0]
    assert record.tool_name == "high_tool"
    assert record.outcome == "denied"


def test_invoke_denied_does_not_publish_event(client_with_registry: TestClient) -> None:
    """Denied invocations must not emit events onto the event bus."""
    bus = _mock_bus()
    app.dependency_overrides[get_event_bus] = lambda: bus

    resp = client_with_registry.post(
        "/mcp/tools/high_tool/invoke",
        json={"parameters": {}, "correlation_id": "cid-denied"},
    )
    assert resp.status_code == 403
    bus.publish.assert_not_called()


# ---------------------------------------------------------------------------
# Tool invocation — 404
# ---------------------------------------------------------------------------


def test_invoke_unknown_tool_returns_404(client_with_registry: TestClient) -> None:
    """Invoking an unregistered tool must return 404."""
    resp = client_with_registry.post("/mcp/tools/nonexistent/invoke", json={"parameters": {}})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tool invocation — dependency failure paths
# ---------------------------------------------------------------------------


def test_invoke_audit_failure_returns_500(client_with_registry: TestClient) -> None:
    """An AuditError from trail.insert must return a structured 500 response."""
    trail = _mock_trail(insert_side_effect=AuditError("db down"))
    app.dependency_overrides[get_audit_trail] = lambda: trail

    resp = client_with_registry.post("/mcp/tools/low_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["error"] == "audit_error"
    assert "db down" in detail["detail"]


def test_invoke_event_bus_failure_returns_500(client_with_registry: TestClient) -> None:
    """An EventBusError from publish must return a structured 500 response."""
    bus = _mock_bus(publish_side_effect=EventBusError("redis down"))
    app.dependency_overrides[get_event_bus] = lambda: bus

    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {}, "correlation_id": "cid-bus"},
    )
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["error"] == "event_bus_error"
    assert "redis down" in detail["detail"]


def test_invoke_approval_gate_failure_returns_500(client_with_registry: TestClient) -> None:
    """An ApprovalError from gate.evaluate must return a structured 500 response."""
    mock_gate = MagicMock()
    mock_gate.evaluate = AsyncMock(side_effect=ApprovalError("gate exploded"))
    app.dependency_overrides[get_approval_gate] = lambda: mock_gate

    resp = client_with_registry.post("/mcp/tools/low_tool/invoke", json={"parameters": {}})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["error"] == "approval_error"
    assert "gate exploded" in detail["detail"]

    app.dependency_overrides.pop(get_approval_gate, None)


def test_invoke_handler_failure_returns_500(
    client_with_registry: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A handler exception during invoke must return a structured 500 response."""
    mock_registry = MagicMock()
    mock_registry.has.return_value = True
    mock_registry.execute = AsyncMock(side_effect=RuntimeError("handler exploded"))
    monkeypatch.setattr("core.gateway.app.handler_registry", mock_registry)

    resp = client_with_registry.post(
        "/mcp/tools/low_tool/invoke",
        json={"parameters": {"x": 1}, "correlation_id": "cid-handler"},
    )
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["error"] == "handler_error"
    assert "handler exploded" in detail["detail"]
    assert detail["correlation_id"] == "cid-handler"


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


# ---------------------------------------------------------------------------
# _resolve_database_url helper
# ---------------------------------------------------------------------------


def test_resolve_database_url_returns_database_url_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DATABASE_URL takes priority over SUPABASE_DB_URL when both are set."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://host/db")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://supabase/db")
    assert _resolve_database_url() == "postgresql://host/db"


def test_resolve_database_url_falls_back_to_supabase_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SUPABASE_DB_URL is used when DATABASE_URL is absent."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://supabase/db")
    assert _resolve_database_url() == "postgresql://supabase/db"


def test_resolve_database_url_returns_none_when_neither_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when neither DATABASE_URL nor SUPABASE_DB_URL is set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert _resolve_database_url() is None


# ---------------------------------------------------------------------------
# Dead-letter endpoint
# ---------------------------------------------------------------------------


def test_dead_letter_no_bus(client_with_registry: TestClient) -> None:
    """GET /events/dead-letter without event bus returns empty list."""
    # Remove event_bus from state if present
    app.state.event_bus = None
    resp = client_with_registry.get("/events/dead-letter")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entries"] == []
    assert body["total"] == 0


def test_dead_letter_with_entries(client_with_registry: TestClient) -> None:
    """GET /events/dead-letter returns entries from the bus."""
    bus = AsyncMock()
    bus.read_dead_letters = AsyncMock(
        return_value=[
            {"msg_id": "1-0", "domain": "test", "dead_letter_reason": "parse error"},
        ]
    )
    app.state.event_bus = bus

    resp = client_with_registry.get("/events/dead-letter")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["entries"][0]["dead_letter_reason"] == "parse error"
    bus.read_dead_letters.assert_called_once_with(count=50)


def test_dead_letter_count_clamped(client_with_registry: TestClient) -> None:
    """GET /events/dead-letter?count=999 is clamped to 200."""
    bus = AsyncMock()
    bus.read_dead_letters = AsyncMock(return_value=[])
    app.state.event_bus = bus

    resp = client_with_registry.get("/events/dead-letter?count=999")
    assert resp.status_code == 200
    bus.read_dead_letters.assert_called_once_with(count=200)
