"""Typed event envelope for the OsMEN-OC event bus.

All messages travelling on the Redis Streams bus MUST be wrapped in an
``EventEnvelope``.  This guarantees a common schema for correlation,
routing, filtering, and dead-letter handling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EventPriority(StrEnum):
    """Priority hint that influences queue ordering on the bus."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EventEnvelope:
    """Immutable container for every event published on the bus.

    Attributes:
        domain: Logical domain owning the event (e.g. ``"media"``, ``"system"``).
        category: Fine-grained event type within the domain
            (e.g. ``"download_complete"``).
        payload: Arbitrary event data.  Callers should use typed Pydantic
            models here; plain ``dict`` is accepted for backwards-compat.
        source: Agent or component that produced the event
            (e.g. ``"media_steward"``).
        event_id: Globally unique identifier, auto-generated as a UUID4.
        correlation_id: Optional identifier that links related events across
            a logical workflow.
        timestamp: UTC creation time, auto-stamped on instantiation.
        priority: Routing/ordering hint; defaults to ``NORMAL``.
        schema_version: Envelope schema version for future migrations.
    """

    domain: str
    category: str
    payload: Any
    source: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    priority: EventPriority = EventPriority.NORMAL
    schema_version: int = 1

    # Redis Streams key derived from domain + category for convenience
    @property
    def stream_key(self) -> str:
        """Return the canonical Redis Streams key for this event.

        Returns:
            Key string following the ``events:{domain}:{category}`` convention.
        """
        return f"events:{self.domain}:{self.category}"

    def to_dict(self) -> dict[str, Any]:
        """Serialise the envelope to a flat ``dict`` suitable for Redis XADD.

        Returns:
            Dictionary with all fields serialised to strings/primitives.
        """
        import json

        return {
            "event_id": self.event_id,
            "domain": self.domain,
            "category": self.category,
            "source": self.source,
            "correlation_id": self.correlation_id or "",
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "schema_version": str(self.schema_version),
            "payload": json.dumps(self.payload) if not isinstance(self.payload, str) else self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventEnvelope:
        """Deserialise an envelope previously produced by :meth:`to_dict`.

        Args:
            data: Flat dictionary as stored in Redis.

        Returns:
            Reconstructed :class:`EventEnvelope`.
        """
        import json

        return cls(
            event_id=data["event_id"],
            domain=data["domain"],
            category=data["category"],
            source=data["source"],
            correlation_id=data.get("correlation_id") or None,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            schema_version=int(data.get("schema_version", 1)),
            payload=json.loads(data["payload"]) if isinstance(data.get("payload"), str) else data.get("payload"),
        )
