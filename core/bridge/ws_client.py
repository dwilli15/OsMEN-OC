"""Reconnecting WebSocket client for OpenClaw bridge traffic."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from core.bridge.protocol import BridgeInboundMessage, BridgeOutboundMessage

SessionFactory = Callable[[str], Any]
MessageHandler = Callable[[BridgeInboundMessage], Awaitable[None]]
SleepFn = Callable[[float], Awaitable[None]]


class OpenClawBridgeClient:
    """Async bridge client with exponential backoff reconnects."""

    def __init__(
        self,
        *,
        endpoint: str = "ws://127.0.0.1:18789",
        on_message: MessageHandler,
        session_factory: SessionFactory | None = None,
        max_backoff_seconds: float = 60.0,
        sleep_fn: SleepFn | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._on_message = on_message
        self._session_factory = session_factory or self._default_session_factory
        self._max_backoff = max_backoff_seconds
        self._sleep = sleep_fn or asyncio.sleep
        self._active_ws: Any | None = None

    @staticmethod
    def _default_session_factory(endpoint: str) -> Any:
        """Create the default websocket session context manager lazily."""
        from websockets.asyncio.client import connect

        return connect(endpoint)

    async def run_forever(self, *, max_cycles: int | None = None) -> None:
        """Run a reconnecting receive loop.

        Args:
            max_cycles: Optional max connection attempts. Intended for tests.
        """
        backoff = 1.0
        cycles = 0

        while True:
            if max_cycles is not None and cycles >= max_cycles:
                return
            cycles += 1

            try:
                async with self._session_factory(self.endpoint) as ws:
                    self._active_ws = ws
                    backoff = 1.0
                    logger.info("OpenClaw bridge connected to {}", self.endpoint)
                    async for raw in ws:
                        message = BridgeInboundMessage.model_validate_json(raw)
                        await self._on_message(message)
            except Exception as exc:
                logger.warning("OpenClaw bridge connection error: {}", exc)
                await self._sleep(backoff)
                backoff = min(backoff * 2.0, self._max_backoff)
            finally:
                self._active_ws = None

    async def send(self, message: BridgeOutboundMessage) -> None:
        """Send an outbound bridge message on the active WebSocket session."""
        if self._active_ws is None:
            raise RuntimeError("Bridge websocket is not connected")
        await self._active_ws.send(message.model_dump_json())
