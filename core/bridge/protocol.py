"""Protocol schemas for OpenClaw <-> OsMEN-OC bridge messages."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BridgeInboundMessage(BaseModel):
    """Inbound message from OpenClaw to OsMEN-OC."""

    type: str
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BridgeOutboundMessage(BaseModel):
    """Outbound message from OsMEN-OC to OpenClaw."""

    type: str
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
