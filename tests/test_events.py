"""Tests for core.events.envelope and core.events.bus."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from core.events.bus import DEAD_LETTER_STREAM, EventBus
from core.events.envelope import EventEnvelope, EventPriority
from core.utils.exceptions import EventBusError

# ---------------------------------------------------------------------------
# EventEnvelope tests
# ---------------------------------------------------------------------------


def test_envelope_defaults():
    """EventEnvelope auto-populates event_id, timestamp, and priority."""
    env = EventEnvelope(
        domain="system",
        category="health_check",
        payload={"status": "ok"},
        source="monitor",
    )
    assert env.event_id  # non-empty UUID
    assert env.timestamp.tzinfo is not None
    assert env.priority == EventPriority.NORMAL
    assert env.schema_version == 1


def test_envelope_stream_key():
    """stream_key follows events:{domain}:{category} convention."""
    env = EventEnvelope(
        domain="media",
        category="download_complete",
        payload={},
        source="media_steward",
    )
    assert env.stream_key == "events:media:download_complete"


def test_envelope_round_trip():
    """to_dict() / from_dict() preserves all fields."""
    original = EventEnvelope(
        domain="media",
        category="transfer",
        payload={"file": "movie.mkv"},
        source="media_steward",
        correlation_id="corr-123",
        priority=EventPriority.HIGH,
    )
    restored = EventEnvelope.from_dict(original.to_dict())

    assert restored.event_id == original.event_id
    assert restored.domain == original.domain
    assert restored.category == original.category
    assert restored.source == original.source
    assert restored.correlation_id == original.correlation_id
    assert restored.priority == original.priority
    assert restored.schema_version == original.schema_version
    assert restored.payload == original.payload


def test_envelope_to_dict_payload_serialised():
    """to_dict() JSON-serialises dict payloads."""
    env = EventEnvelope(
        domain="test",
        category="ping",
        payload={"key": "value"},
        source="test_agent",
    )
    data = env.to_dict()
    # payload must be a JSON string in the flat dict
    assert isinstance(data["payload"], str)
    assert json.loads(data["payload"]) == {"key": "value"}


def test_envelope_empty_correlation_id_round_trip():
    """Empty correlation_id is normalised to None on round-trip."""
    env = EventEnvelope(
        domain="test",
        category="ping",
        payload={},
        source="test_agent",
        correlation_id=None,
    )
    restored = EventEnvelope.from_dict(env.to_dict())
    assert restored.correlation_id is None


# ---------------------------------------------------------------------------
# EventBus tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_event_bus_publish(mock_redis):
    """publish() calls xadd with the correct stream key and returns msg_id."""
    bus = EventBus(mock_redis)
    env = EventEnvelope(
        domain="media",
        category="download_complete",
        payload={"file": "test.mkv"},
        source="media_steward",
    )
    msg_id = await bus.publish(env)

    assert msg_id == "1-0"
    mock_redis.xadd.assert_called_once_with(
        "events:media:download_complete",
        env.to_dict(),
    )


@pytest.mark.anyio
async def test_event_bus_publish_raises_on_redis_error(mock_redis):
    """publish() wraps Redis exceptions in EventBusError."""
    mock_redis.xadd = AsyncMock(side_effect=RuntimeError("connection refused"))
    bus = EventBus(mock_redis)
    env = EventEnvelope(
        domain="system",
        category="alert",
        payload={},
        source="monitor",
    )
    with pytest.raises(EventBusError):
        await bus.publish(env)


@pytest.mark.anyio
async def test_event_bus_dead_letter(mock_redis):
    """_dead_letter() writes a message to DEAD_LETTER_STREAM."""
    bus = EventBus(mock_redis)
    await bus._dead_letter(
        original_msg_id="99-0",
        original_stream="events:test:fail",
        fields={"event_id": "abc"},
        reason="parse error",
    )
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == DEAD_LETTER_STREAM
    assert call_args[0][1]["dead_letter_reason"] == "parse error"
    assert call_args[0][1]["original_stream"] == "events:test:fail"


@pytest.mark.anyio
async def test_event_bus_ensure_group_swallows_busy_error(mock_redis):
    """_ensure_group() ignores BUSYGROUP errors (group already exists)."""
    mock_redis.xgroup_create = AsyncMock(side_effect=Exception("BUSYGROUP"))
    bus = EventBus(mock_redis)
    # Should not raise
    await bus._ensure_group("events:media:download_complete")


@pytest.mark.anyio
async def test_replay_dead_letters_replays_and_deletes_when_requested(mock_redis):
    """replay_dead_letters replays to original stream and can delete source entries."""
    mock_redis.xrange = AsyncMock(
        return_value=[
            (
                "10-0",
                {
                    "event_id": "e1",
                    "payload": '{"k":"v"}',
                    "original_stream": "events:test:source",
                    "original_msg_id": "1-0",
                    "dead_letter_reason": "parse",
                },
            ),
        ]
    )
    mock_redis.xadd = AsyncMock(return_value="11-0")
    mock_redis.xdel = AsyncMock(return_value=1)

    bus = EventBus(mock_redis)
    summary = await bus.replay_dead_letters(count=10, delete_replayed=True)

    assert summary["inspected"] == 1
    assert summary["replayed"] == 1
    assert summary["errors"] == 0
    mock_redis.xadd.assert_any_call(
        "events:test:source",
        {"event_id": "e1", "payload": '{"k":"v"}'},
    )
    mock_redis.xdel.assert_awaited_once_with(DEAD_LETTER_STREAM, "10-0")


@pytest.mark.anyio
async def test_replay_dead_letters_skips_entries_without_original_stream(mock_redis):
    """replay_dead_letters skips malformed dead-letter entries safely."""
    mock_redis.xrange = AsyncMock(return_value=[("10-0", {"event_id": "e1"})])
    mock_redis.xadd = AsyncMock(return_value="11-0")

    bus = EventBus(mock_redis)
    summary = await bus.replay_dead_letters(count=10)

    assert summary["inspected"] == 1
    assert summary["skipped"] == 1
    assert summary["replayed"] == 0
