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


def get_audit_trail(request: Request) -> AuditTrail:
    """Return an :class:`~core.audit.trail.AuditTrail` backed by the app's pg pool.

    The pool must be stored in ``app.state.pg_pool`` before any invoke
    requests are handled (set during the ``lifespan`` startup phase or
    overridden via ``app.dependency_overrides`` in tests).
    """
    return AuditTrail(request.app.state.pg_pool)


MCPRegistry = Annotated[dict[str, Any], Depends(get_mcp_registry)]
ApprovalGateDep = Annotated[ApprovalGate, Depends(get_approval_gate)]
AuditTrailDep = Annotated[AuditTrail, Depends(get_audit_trail)]
