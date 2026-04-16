"""FastAPI dependency injection stubs.

These providers are injected into route handlers via ``Depends()``.
All clients are initialized once at startup (stored in ``app.state``) and
retrieved here without re-allocating on every request.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request

from core.approval.gate import ApprovalGate
from core.audit.trail import AuditTrail
from core.events.bus import EventBus
from core.utils.exceptions import EventBusError


class _NoopEventBus:
    """Fallback bus used during bootstrap/tests when Redis is not configured."""

    async def publish(self, _envelope: Any) -> str:
        return "noop"

    async def read_dead_letters(self, **_kwargs: Any) -> list[Any]:
        raise EventBusError("Event bus not configured")

    async def replay_dead_letters(self, **_kwargs: Any) -> dict[str, Any]:
        raise EventBusError("Event bus not configured")


def get_mcp_registry(request: Request) -> dict[str, Any]:
    """Return the MCP tool registry stored in app state.

    Populated during the ``lifespan`` startup phase in ``app.py``.
    """
    return request.app.state.mcp_registry  # type: ignore[no-any-return]


def get_approval_gate(request: Request) -> ApprovalGate:
    """Return the :class:`~core.approval.gate.ApprovalGate` from app state.

    Falls back to a default (no approval callback) instance if one has not
    been stored in ``app.state`` — suitable for low/medium risk evaluation in
    tests and during early bootstrap.
    """
    return getattr(request.app.state, "approval_gate", ApprovalGate())




def get_event_bus(request: Request) -> EventBus | _NoopEventBus:
    """Return an event bus instance from app state.

    If ``app.state.event_bus`` is absent, return a no-op publisher so gateway
    routes can run in early bootstrap and isolated tests.
    """
    return getattr(request.app.state, "event_bus", _NoopEventBus())


def get_audit_trail(request: Request) -> AuditTrail | None:
    """Return the AuditTrail from app state, or None if not configured."""
    return getattr(request.app.state, "audit_trail", None)


MCPRegistry = Annotated[dict[str, Any], Depends(get_mcp_registry)]
ApprovalGateDep = Annotated[ApprovalGate, Depends(get_approval_gate)]
AuditTrailDep = Annotated[AuditTrail | None, Depends(get_audit_trail)]
EventBusDep = Annotated[EventBus | _NoopEventBus, Depends(get_event_bus)]
