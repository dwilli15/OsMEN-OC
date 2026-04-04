"""Tests for WebSocket bridge dispatch in core/gateway/app.py.

Covers:
- Valid BridgeInboundMessage is parsed and dispatches to event bus.
- Invalid JSON gets a nack response.
- Acknowledgment includes correct type and correlation_id.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from core.bridge.protocol import BridgeInboundMessage
from core.gateway.app import app
from core.gateway.deps import get_event_bus
from core.gateway.mcp import MCPTool


def _make_registry() -> dict[str, MCPTool]:
    return {"dummy": MCPTool(agent_id="test", name="dummy", risk_level="low")}


def _mock_bus() -> AsyncMock:
    bus = AsyncMock()
    bus.publish = AsyncMock(return_value="1-0")
    return bus


class TestWebSocketBridge:
    """Tests for the /ws WebSocket endpoint."""

    def test_valid_message_dispatches_and_acks(self) -> None:
        bus = _mock_bus()
        app.dependency_overrides[get_event_bus] = lambda: bus

        with TestClient(app) as client:
            app.state.mcp_registry = _make_registry()
            app.state.event_bus = bus

            with client.websocket_connect("/ws") as ws:
                msg = BridgeInboundMessage(
                    type="task_request",
                    correlation_id="cid-ws-1",
                    payload={"action": "do_thing"},
                )
                ws.send_text(msg.model_dump_json())
                ack = ws.receive_json()

                assert ack["type"] == "ack"
                assert ack["correlation_id"] == "cid-ws-1"
                assert ack["payload"]["received_type"] == "task_request"

        app.dependency_overrides.pop(get_event_bus, None)

    def test_valid_message_publishes_event(self) -> None:
        bus = _mock_bus()
        app.dependency_overrides[get_event_bus] = lambda: bus

        with TestClient(app) as client:
            app.state.mcp_registry = _make_registry()
            app.state.event_bus = bus

            with client.websocket_connect("/ws") as ws:
                msg = BridgeInboundMessage(
                    type="task_request",
                    correlation_id="cid-ws-2",
                    payload={"x": 1},
                )
                ws.send_text(msg.model_dump_json())
                ws.receive_json()  # consume ack

            bus.publish.assert_called_once()
            envelope = bus.publish.call_args[0][0]
            assert envelope.domain == "bridge"
            assert envelope.category == "task_request"
            assert envelope.correlation_id == "cid-ws-2"
            assert envelope.payload == {"x": 1}

        app.dependency_overrides.pop(get_event_bus, None)

    def test_invalid_json_returns_nack(self) -> None:
        bus = _mock_bus()
        app.dependency_overrides[get_event_bus] = lambda: bus

        with TestClient(app) as client:
            app.state.mcp_registry = _make_registry()
            app.state.event_bus = bus

            with client.websocket_connect("/ws") as ws:
                ws.send_text("not valid json {{{")
                resp = ws.receive_json()
                assert resp["ack"] is False
                assert "error" in resp

        app.dependency_overrides.pop(get_event_bus, None)
