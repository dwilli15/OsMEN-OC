"""OpenClaw bridge client primitives."""

from __future__ import annotations

from core.bridge.protocol import BridgeInboundMessage, BridgeOutboundMessage
from core.bridge.ws_client import OpenClawBridgeClient

__all__ = ["BridgeInboundMessage", "BridgeOutboundMessage", "OpenClawBridgeClient"]
