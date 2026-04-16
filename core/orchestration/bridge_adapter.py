"""Bridge adapter — routes OpenClaw bridge messages to the orchestration engine.

When an inbound bridge message arrives (via ``core/bridge/ws_client.py``),
this adapter classifies the message type, determines whether it should
trigger a workflow, and dispatches it to the appropriate engine.

Bridge message routing:

- ``task_request`` → Session classifier → Cooperative engine (Mode A)
- ``conversation`` → Session classifier → Discussion engine (Mode B)
- ``heartbeat`` → Ignored (handled by gateway health checks)
- ``approval_response`` → Resolves a pending APPROVAL interrupt
- Other → Logged and dropped

The adapter is registered as a handler on the event bus domain
``bridge`` and is the single entry point from the bridge layer
into orchestration.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from core.bridge.protocol import BridgeInboundMessage
from core.events.envelope import EventEnvelope, EventPriority
from core.orchestration.models import (
    Interrupt,
    InterruptKind,
    WorkflowMode,
    WorkflowStatus,
)
from core.orchestration.session import SessionClassifier
from core.orchestration.workflow import CooperativeEngine
from core.orchestration.discussion import DiscussionEngine


class BridgeAdapter:
    """Routes bridge messages to orchestration engines.

    Args:
        session_classifier: For workflow creation/resumption decisions.
        cooperative_engine: Mode A engine for task-type requests.
        discussion_engine: Mode B engine for conversation-type requests.
    """

    def __init__(
        self,
        session_classifier: SessionClassifier,
        cooperative_engine: CooperativeEngine,
        discussion_engine: DiscussionEngine,
    ) -> None:
        self._classifier = session_classifier
        self._cooperative = cooperative_engine
        self._discussion = discussion_engine

    async def handle_message(
        self,
        msg: BridgeInboundMessage,
        *,
        source_channel: str = "bridge",
    ) -> EventEnvelope | None:
        """Process an inbound bridge message.

        Returns an EventEnvelope if the message was routed to a workflow,
        or None if it was ignored/dropped.
        """
        msg_type = msg.type
        correlation_id = msg.correlation_id
        payload = msg.payload

        logger.debug(
            "bridge_adapter: type={} correlation={}",
            msg_type,
            correlation_id,
        )

        if msg_type == "task_request":
            return await self._handle_task_request(
                payload, correlation_id, source_channel
            )
        elif msg_type == "conversation":
            return await self._handle_conversation(
                payload, correlation_id, source_channel
            )
        elif msg_type == "approval_response":
            return await self._handle_approval_response(payload, correlation_id)
        elif msg_type == "heartbeat":
            # Silently ignore heartbeats — they're handled by gateway health checks
            return None
        else:
            logger.debug("bridge_adapter: unhandled message type {}", msg_type)
            return None

    # ── Internal ────────────────────────────────────────────────────────────

    async def _handle_task_request(
        self,
        payload: dict[str, Any],
        correlation_id: str | None,
        source_channel: str,
    ) -> EventEnvelope | None:
        """Route a task request to Mode A cooperative workflow."""
        request_text = payload.get("text", payload.get("request", ""))
        if not request_text:
            logger.warning("bridge_adapter: task_request with no text payload")
            return None

        workflow_id, is_new = await self._classifier.classify(
            request_text,
            correlation_id=correlation_id,
            source_channel=source_channel,
            mode=WorkflowMode.COOPERATIVE,
        )

        if is_new:
            logger.info(
                "bridge_adapter: created workflow {} for task_request",
                workflow_id,
            )
        else:
            logger.info(
                "bridge_adapter: resuming workflow {} for task_request",
                workflow_id,
            )

        return EventEnvelope(
            domain="orchestration",
            category="workflow_created" if is_new else "workflow_resumed",
            payload={
                "workflow_id": workflow_id,
                "is_new": is_new,
                "request": request_text,
                "source": "bridge",
                "mode": "cooperative",
            },
            source="bridge_adapter",
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
        )

    async def _handle_conversation(
        self,
        payload: dict[str, Any],
        correlation_id: str | None,
        source_channel: str,
    ) -> EventEnvelope | None:
        """Route a conversation message to Mode B discussion."""
        request_text = payload.get("text", payload.get("message", ""))
        if not request_text:
            logger.warning("bridge_adapter: conversation with no text payload")
            return None

        workflow_id, is_new = await self._classifier.classify(
            request_text,
            correlation_id=correlation_id,
            source_channel=source_channel,
            mode=WorkflowMode.DISCUSSION,
        )

        if is_new:
            await self._discussion.start_discussion(workflow_id)

        return EventEnvelope(
            domain="orchestration",
            category="discussion_started" if is_new else "discussion_resumed",
            payload={
                "workflow_id": workflow_id,
                "is_new": is_new,
                "request": request_text,
                "source": "bridge",
                "mode": "discussion",
            },
            source="bridge_adapter",
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
        )

    async def _handle_approval_response(
        self,
        payload: dict[str, Any],
        correlation_id: str | None,
    ) -> EventEnvelope | None:
        """Handle an approval response — resolves a pending APPROVAL interrupt."""
        workflow_id = payload.get("workflow_id")
        approved = payload.get("approved", False)

        if not workflow_id:
            logger.warning("bridge_adapter: approval_response missing workflow_id")
            return None

        # The approval response is handled by the cooperative engine's
        # interrupt resolution mechanism.  We emit an event so the engine
        # can pick it up.
        resolution = "resumed" if approved else "aborted"

        return EventEnvelope(
            domain="orchestration",
            category="approval_resolved",
            payload={
                "workflow_id": workflow_id,
                "approved": approved,
                "resolution": resolution,
            },
            source="bridge_adapter",
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
        )
