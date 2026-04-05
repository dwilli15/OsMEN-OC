"""Tool handler registry for OsMEN-OC.

Maps MCP tool names to async Python callables so pipeline steps and
direct invocations can execute real work (web scraping, RAG ingest,
media transfer, etc.) instead of only flowing through the approval/audit
path.

Usage::

    from core.gateway.handlers import handler_registry, register_handler

    @register_handler("ingest_url")
    async def handle_ingest_url(parameters: dict, context: HandlerContext) -> dict:
        ...

    # At invocation time:
    result = await handler_registry.execute("ingest_url", params, context)
"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class HandlerContext:
    """Runtime context passed to every tool handler.

    Attributes:
        agent_id: The agent that owns the tool.
        correlation_id: Optional trace correlation.
        app_state: Reference to ``app.state`` for accessing shared clients.
    """

    agent_id: str
    correlation_id: str | None = None
    app_state: Any = None


HandlerFn = Callable[[dict[str, Any], HandlerContext], Awaitable[dict[str, Any]]]


class HandlerRegistry:
    """Name-keyed registry of async tool handler functions."""

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFn] = {}

    def register(self, tool_name: str, fn: HandlerFn) -> None:
        """Register *fn* as the handler for *tool_name*."""
        if tool_name in self._handlers:
            logger.warning("Overwriting handler for tool '{}'", tool_name)
        self._handlers[tool_name] = fn
        logger.debug("Registered handler for tool '{}'", tool_name)

    def get(self, tool_name: str) -> HandlerFn | None:
        """Return the handler for *tool_name*, or ``None``."""
        return self._handlers.get(tool_name)

    def has(self, tool_name: str) -> bool:
        """Return ``True`` if a handler is registered for *tool_name*."""
        return tool_name in self._handlers

    async def execute(
        self, tool_name: str, parameters: dict[str, Any], context: HandlerContext
    ) -> dict[str, Any]:
        """Look up and call the handler for *tool_name*.

        Returns:
            Result dict from the handler.

        Raises:
            KeyError: If no handler is registered.
        """
        fn = self._handlers.get(tool_name)
        if fn is None:
            raise KeyError(f"No handler registered for tool {tool_name!r}")
        return await fn(parameters, context)

    @property
    def registered_tools(self) -> list[str]:
        """Return names of all registered tools."""
        return list(self._handlers.keys())


# Module-level singleton
handler_registry = HandlerRegistry()


def register_handler(tool_name: str) -> Callable[[HandlerFn], HandlerFn]:
    """Decorator to register a tool handler on the global registry.

    Usage::

        @register_handler("ingest_url")
        async def handle_ingest(params, ctx):
            ...
    """

    def decorator(fn: HandlerFn) -> HandlerFn:
        handler_registry.register(tool_name, fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Entry-point plugin loader
# ---------------------------------------------------------------------------

ENTRY_POINT_GROUP = "osmen_oc.handlers"


def load_entry_point_handlers(
    registry: HandlerRegistry | None = None,
) -> list[str]:
    """Discover and register handlers advertised via ``[project.entry-points]``.

    Each entry point in the ``osmen_oc.handlers`` group should resolve to an
    async callable with the standard ``(params, context) -> dict`` signature.
    The entry point *name* becomes the tool name in the registry.

    Args:
        registry: Registry to populate.  Defaults to the module-level
            :data:`handler_registry` singleton.

    Returns:
        List of tool names that were successfully loaded.
    """
    if registry is None:
        registry = handler_registry

    loaded: list[str] = []
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    for ep in eps:
        try:
            handler_fn = ep.load()
            registry.register(ep.name, handler_fn)
            loaded.append(ep.name)
            logger.info("Loaded plugin handler '{}' from {}", ep.name, ep.value)
        except Exception as exc:
            logger.warning("Failed to load plugin handler '{}': {}", ep.name, exc)

    return loaded
