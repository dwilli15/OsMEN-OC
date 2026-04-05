"""Tests for OpenClaw bridge protocol and reconnecting websocket client."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from core.bridge.protocol import BridgeInboundMessage, BridgeOutboundMessage
from core.bridge.ws_client import OpenClawBridgeClient


class _FakeWebSocket:
    def __init__(self, messages: list[str]):
        self._messages = messages
        self.sent: list[str] = []

    def __aiter__(self) -> AsyncIterator[str]:
        async def _iter() -> AsyncIterator[str]:
            for item in self._messages:
                yield item

        return _iter()

    async def send(self, payload: str) -> None:
        self.sent.append(payload)


class _FakeSession:
    def __init__(self, ws: _FakeWebSocket):
        self._ws = ws

    async def __aenter__(self) -> _FakeWebSocket:
        return self._ws

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _SessionFactoryQueue:
    def __init__(self, sessions: list[_FakeSession]):
        self._sessions = sessions

    def __call__(self, _endpoint: str) -> _FakeSession:
        if not self._sessions:
            raise RuntimeError("no sessions available")
        return self._sessions.pop(0)


def test_protocol_models_roundtrip() -> None:
    outbound = BridgeOutboundMessage(type="tool_result", correlation_id="cid", payload={"ok": True})
    encoded = outbound.model_dump_json()
    inbound = BridgeInboundMessage.model_validate_json(encoded)

    assert inbound.type == "tool_result"
    assert inbound.correlation_id == "cid"
    assert inbound.payload["ok"] is True


@pytest.mark.anyio
async def test_bridge_client_dispatches_messages() -> None:
    received: list[BridgeInboundMessage] = []

    async def on_message(msg: BridgeInboundMessage) -> None:
        received.append(msg)

    ws = _FakeWebSocket(
        [BridgeInboundMessage(type="task", correlation_id="a1", payload={"x": 1}).model_dump_json()]
    )

    client = OpenClawBridgeClient(
        endpoint="ws://test",
        on_message=on_message,
        session_factory=lambda _endpoint: _FakeSession(ws),
    )

    await client.run_forever(max_cycles=1)

    assert len(received) == 1
    assert received[0].type == "task"
    assert received[0].payload["x"] == 1


@pytest.mark.anyio
async def test_bridge_client_send_requires_connection() -> None:
    async def on_message(_msg: BridgeInboundMessage) -> None:
        return

    client = OpenClawBridgeClient(endpoint="ws://test", on_message=on_message)

    with pytest.raises(RuntimeError, match="not connected"):
        await client.send(BridgeOutboundMessage(type="ping"))


@pytest.mark.anyio
async def test_bridge_client_reconnect_backoff_caps() -> None:
    sleeps: list[float] = []

    async def on_message(_msg: BridgeInboundMessage) -> None:
        return

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    class _FailingSession:
        async def __aenter__(self):
            raise RuntimeError("connect fail")

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    client = OpenClawBridgeClient(
        endpoint="ws://test",
        on_message=on_message,
        session_factory=lambda _endpoint: _FailingSession(),
        max_backoff_seconds=3.0,
        sleep_fn=fake_sleep,
    )

    await client.run_forever(max_cycles=4)

    assert sleeps == [1.0, 2.0, 3.0, 3.0]


@pytest.mark.anyio
async def test_bridge_client_skips_malformed_message_and_continues_same_session() -> None:
    received: list[BridgeInboundMessage] = []
    sleeps: list[float] = []

    async def on_message(msg: BridgeInboundMessage) -> None:
        received.append(msg)

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    ws = _FakeWebSocket(
        [
            '{"type":"task","payload":["bad"]}',
            BridgeInboundMessage(
                type="task", correlation_id="a1", payload={"x": 1},
            ).model_dump_json(),
        ]
    )
    factory = _SessionFactoryQueue([_FakeSession(ws)])

    client = OpenClawBridgeClient(
        endpoint="ws://test",
        on_message=on_message,
        session_factory=factory,
        sleep_fn=fake_sleep,
    )

    await client.run_forever(max_cycles=1)

    assert sleeps == []
    assert len(received) == 1
    assert received[0].correlation_id == "a1"
    assert received[0].payload["x"] == 1
