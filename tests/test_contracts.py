"""Contract tests for bridge protocol and event envelope schemas.

These tests verify that the wire-format contracts between OsMEN-OC
components remain stable.  Any schema change that breaks serialisation
round-trips will fail here, acting as an early warning before
integration defects surface at runtime.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from core.bridge.protocol import BridgeInboundMessage, BridgeOutboundMessage
from core.events.envelope import EventEnvelope, EventPriority

# ---------------------------------------------------------------------------
# Bridge protocol contracts
# ---------------------------------------------------------------------------


class TestBridgeProtocolContracts:
    """Ensure inbound/outbound bridge messages survive JSON round-trips."""

    def test_outbound_to_inbound_roundtrip(self) -> None:
        out = BridgeOutboundMessage(
            type="tool_result",
            correlation_id="corr-1",
            payload={"status": "ok", "value": 42},
        )
        raw = out.model_dump_json()
        inb = BridgeInboundMessage.model_validate_json(raw)

        assert inb.type == out.type
        assert inb.correlation_id == out.correlation_id
        assert inb.payload == out.payload

    def test_inbound_to_outbound_roundtrip(self) -> None:
        inb = BridgeInboundMessage(
            type="task",
            correlation_id="corr-2",
            payload={"agent": "daily_brief", "tool": "fetch_task_summary"},
        )
        raw = inb.model_dump_json()
        out = BridgeOutboundMessage.model_validate_json(raw)

        assert out.type == inb.type
        assert out.correlation_id == inb.correlation_id
        assert out.payload == inb.payload

    def test_minimal_message_defaults(self) -> None:
        inb = BridgeInboundMessage(type="ping")
        assert inb.correlation_id is None
        assert inb.payload == {}

        out = BridgeOutboundMessage(type="pong")
        assert out.correlation_id is None
        assert out.payload == {}

    def test_nested_payload_preserved(self) -> None:
        nested = {"a": {"b": [1, 2, {"c": True}]}}
        out = BridgeOutboundMessage(type="data", payload=nested)
        raw = out.model_dump_json()
        inb = BridgeInboundMessage.model_validate_json(raw)
        assert inb.payload == nested

    def test_extra_fields_rejected(self) -> None:
        """Unknown fields should not silently appear in the model."""
        raw = json.dumps({"type": "test", "unknown_field": "bad"})
        msg = BridgeInboundMessage.model_validate_json(raw)
        assert not hasattr(msg, "unknown_field")

    def test_missing_type_raises(self) -> None:
        with pytest.raises(Exception):
            BridgeInboundMessage.model_validate_json('{"payload": {}}')


# ---------------------------------------------------------------------------
# EventEnvelope contracts
# ---------------------------------------------------------------------------


class TestEventEnvelopeContracts:
    """Ensure EventEnvelope serialises and deserialises losslessly."""

    def test_to_dict_from_dict_roundtrip(self) -> None:
        original = EventEnvelope(
            domain="media",
            category="download_complete",
            source="media_steward",
            payload={"url": "https://example.com/file.mp4", "size_mb": 512},
            correlation_id="wf-123",
            priority=EventPriority.HIGH,
        )
        serialised = original.to_dict()
        restored = EventEnvelope.from_dict(serialised)

        assert restored.domain == original.domain
        assert restored.category == original.category
        assert restored.source == original.source
        assert restored.payload == original.payload
        assert restored.correlation_id == original.correlation_id
        assert restored.priority == original.priority
        assert restored.event_id == original.event_id
        assert restored.schema_version == original.schema_version

    def test_timestamp_survives_roundtrip(self) -> None:
        now = datetime.now(UTC)
        env = EventEnvelope(
            domain="test",
            category="ts_check",
            source="unit",
            payload={},
            timestamp=now,
        )
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored.timestamp == now

    def test_stream_key_convention(self) -> None:
        env = EventEnvelope(
            domain="pipelines",
            category="step_completed",
            source="runner",
            payload={},
        )
        assert env.stream_key == "events:pipelines:step_completed"

    def test_default_priority_is_normal(self) -> None:
        env = EventEnvelope(
            domain="d", category="c", source="s", payload={}
        )
        assert env.priority == EventPriority.NORMAL

    def test_null_correlation_id_roundtrip(self) -> None:
        env = EventEnvelope(
            domain="d",
            category="c",
            source="s",
            payload={},
            correlation_id=None,
        )
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored.correlation_id is None

    def test_dict_payload_roundtrips_as_json(self) -> None:
        payload = {"nested": {"list": [1, 2, 3], "flag": True}}
        env = EventEnvelope(
            domain="d", category="c", source="s", payload=payload
        )
        serialised = env.to_dict()
        assert isinstance(serialised["payload"], str)
        assert json.loads(serialised["payload"]) == payload

    def test_string_payload_stays_string(self) -> None:
        env = EventEnvelope(
            domain="d", category="c", source="s", payload="raw-string"
        )
        serialised = env.to_dict()
        assert serialised["payload"] == "raw-string"

    def test_all_priority_values_roundtrip(self) -> None:
        for prio in EventPriority:
            env = EventEnvelope(
                domain="d", category="c", source="s",
                payload={}, priority=prio,
            )
            restored = EventEnvelope.from_dict(env.to_dict())
            assert restored.priority == prio
