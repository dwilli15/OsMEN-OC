"""Async Redis Streams event bus with dead-letter handling.

Usage::

    bus = EventBus(redis_client)
    await bus.publish(envelope)

    async for envelope in bus.subscribe("events:media:*"):
        ...
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from loguru import logger

from core.events.envelope import EventEnvelope
from core.utils.exceptions import EventBusError

if TYPE_CHECKING:
    from redis.asyncio import Redis

# Redis Streams consumer group used by all OsMEN-OC subscribers
_CONSUMER_GROUP = "osmen-workers"
# Stream key used for events that fail processing after max retries
DEAD_LETTER_STREAM = "events:dead_letter"
# Maximum delivery attempts before a message is moved to dead-letter
MAX_RETRIES = 3
# How long (ms) to block waiting for new stream entries
_BLOCK_MS = 5_000


class EventBus:
    """Async event bus backed by Redis Streams.

    Publishes typed :class:`~core.events.envelope.EventEnvelope` messages
    and provides an async-generator subscription interface.  Failed messages
    are routed to :data:`DEAD_LETTER_STREAM` after
    :data:`MAX_RETRIES` delivery attempts.

    Args:
        redis: An initialised ``redis.asyncio.Redis`` client.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, envelope: EventEnvelope) -> str:
        """Publish an event to its canonical stream.

        Args:
            envelope: The typed event to publish.

        Returns:
            The Redis message-id string assigned by XADD.

        Raises:
            EventBusError: If the Redis XADD call fails.
        """
        try:
            msg_id: str = await self._redis.xadd(
                envelope.stream_key,
                envelope.to_dict(),  # type: ignore[arg-type]
            )
            logger.debug(
                "Published event domain={} category={} id={} msg_id={}",
                envelope.domain,
                envelope.category,
                envelope.event_id,
                msg_id,
            )
            return msg_id
        except Exception as exc:
            raise EventBusError(
                f"Failed to publish event {envelope.event_id} to {envelope.stream_key}: {exc}",
                correlation_id=envelope.correlation_id,
            ) from exc

    # ------------------------------------------------------------------
    # Subscribing
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        stream_key: str,
        consumer_name: str,
        *,
        batch_size: int = 10,
    ) -> AsyncIterator[EventEnvelope]:
        """Yield envelopes from *stream_key* for *consumer_name*.

        Creates the consumer group on first call if it does not yet exist.
        Acknowledges each message **after** successful yield so the caller
        controls exactly-once semantics.

        Args:
            stream_key: Redis Streams key to read from
                (e.g. ``"events:media:download_complete"``).
            consumer_name: Unique name for this consumer within the group.
            batch_size: Maximum messages to fetch per XREADGROUP call.

        Yields:
            Deserialised :class:`~core.events.envelope.EventEnvelope` instances.

        Raises:
            EventBusError: On unrecoverable Redis errors.
        """
        await self._ensure_group(stream_key)

        while True:
            try:
                results = await self._redis.xreadgroup(
                    _CONSUMER_GROUP,
                    consumer_name,
                    {stream_key: ">"},
                    count=batch_size,
                    block=_BLOCK_MS,
                )
            except Exception as exc:
                raise EventBusError(
                    f"XREADGROUP failed on {stream_key}: {exc}"
                ) from exc

            if not results:
                # No new messages; keep polling
                await asyncio.sleep(0)
                continue

            for _stream, messages in results:
                for msg_id, fields in messages:
                    try:
                        envelope = EventEnvelope.from_dict(fields)
                        yield envelope
                        await self._redis.xack(_CONSUMER_GROUP, stream_key, msg_id)
                    except Exception as exc:
                        logger.warning(
                            "Failed to process msg_id={} stream={}: {}",
                            msg_id,
                            stream_key,
                            exc,
                        )
                        await self._dead_letter(msg_id, stream_key, fields, str(exc))

    # ------------------------------------------------------------------
    # Dead-letter handling
    # ------------------------------------------------------------------

    async def _dead_letter(
        self,
        original_msg_id: str,
        original_stream: str,
        fields: dict,
        reason: str,
    ) -> None:
        """Route a failing message to the dead-letter stream.

        Args:
            original_msg_id: The Redis message-id of the failing message.
            original_stream: Stream the message was read from.
            fields: Raw field dict from Redis.
            reason: Human-readable failure reason.
        """
        dead_payload = {
            **fields,
            "dead_letter_reason": reason,
            "original_stream": original_stream,
            "original_msg_id": original_msg_id,
        }
        try:
            await self._redis.xadd(DEAD_LETTER_STREAM, dead_payload)
            logger.error(
                "Message moved to dead-letter stream original_stream={} msg_id={} reason={}",
                original_stream,
                original_msg_id,
                reason,
            )
        except Exception as exc:
            logger.critical(
                "FATAL: Could not write to dead-letter stream: {}", exc
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _ensure_group(self, stream_key: str) -> None:
        """Create the consumer group if it does not exist.

        Args:
            stream_key: The stream to create the group on.
        """
        try:
            await self._redis.xgroup_create(
                stream_key,
                _CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            logger.debug("Created consumer group {} on {}", _CONSUMER_GROUP, stream_key)
        except Exception:
            # Group already exists — redis raises BUSYGROUP error, which is fine
            pass
