"""FastAPI application for OsMEN-OC gateway.

Responsibilities
----------------
- Expose ``/health`` liveness probe.
- Expose ``/mcp/tools`` — list all registered MCP tools.
- Expose ``/mcp/tools/{tool_name}/invoke`` — invoke a tool through the
  :class:`~core.approval.gate.ApprovalGate` and persist the result via
  :class:`~core.audit.trail.AuditTrail`.
- At startup: scan ``agents/*.yaml`` and populate the MCP tool registry.
- Accept WebSocket connections from OpenClaw at ``ws://127.0.0.1:18789``.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from core.approval.gate import ApprovalOutcome, ApprovalRequest, RiskLevel
from core.audit.trail import AuditRecord
from core.gateway.deps import ApprovalGateDep, AuditTrailDep, MCPRegistry
from core.gateway.mcp import MCPTool, register_tools, scan_manifests
from core.utils.exceptions import ApprovalError, AuditError

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    agents_dir = Path(os.environ.get("OSMEN_AGENTS_DIR", "agents"))
    logger.info("Gateway startup — scanning agent manifests in {}", agents_dir)

    tools = scan_manifests(agents_dir)
    app.state.mcp_registry = register_tools(tools)

    logger.info("Gateway ready. {} MCP tools registered.", len(app.state.mcp_registry))
    yield
    logger.info("Gateway shutdown.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OsMEN-OC Gateway",
    description=(
        "Execution-engine gateway: REST + MCP tool endpoints + OpenClaw WebSocket bridge."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe — always returns ``{"status": "ok"}``."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# MCP tool list
# ---------------------------------------------------------------------------


class ToolSummary(BaseModel):
    name: str
    agent_id: str
    description: str
    risk_level: str


@app.get("/mcp/tools", response_model=list[ToolSummary], tags=["mcp"])
async def list_tools(registry: MCPRegistry) -> list[ToolSummary]:
    """Return every registered MCP tool with its metadata."""
    return [
        ToolSummary(
            name=tool.name,
            agent_id=tool.agent_id,
            description=tool.description,
            risk_level=tool.risk_level,
        )
        for tool in registry.values()
    ]


# ---------------------------------------------------------------------------
# MCP tool invocation
# ---------------------------------------------------------------------------


class InvokeRequest(BaseModel):
    parameters: dict[str, Any] = {}
    correlation_id: str | None = None


class InvokeResponse(BaseModel):
    tool_name: str
    status: str
    result: Any = None
    message: str = ""


@app.post(
    "/mcp/tools/{tool_name}/invoke",
    response_model=InvokeResponse,
    tags=["mcp"],
)
async def invoke_tool(
    tool_name: str,
    body: InvokeRequest,
    registry: MCPRegistry,
    gate: ApprovalGateDep,
    trail: AuditTrailDep,
) -> InvokeResponse:
    """Invoke a registered MCP tool by name.

    Every invocation is evaluated through the :class:`~core.approval.gate.ApprovalGate`
    before a result is returned, and an :class:`~core.audit.trail.AuditRecord` is
    written via the injected :class:`~core.audit.trail.AuditTrail` dependency.

    Returns:
        - ``200 OK`` with ``status="ok"`` for approved low-risk tools.
        - ``200 OK`` with ``status="queued"`` for approved tools flagged for
          the daily summary (medium-risk).
        - ``403 Forbidden`` with a structured JSON error body when the gate
          denies the request (high/critical risk without a configured approval
          callback, or explicit human denial).
        - ``500 Internal Server Error`` with a structured JSON error body when
          the approval gate or audit trail raise an unexpected error.
        - ``404 Not Found`` when the tool is not in the registry.
    """
    tool: MCPTool | None = registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name!r} not registered")

    approval_req = ApprovalRequest(
        tool_name=tool_name,
        agent_id=tool.agent_id,
        risk_level=RiskLevel(tool.risk_level),
        parameters=body.parameters,
        correlation_id=body.correlation_id,
    )

    # --- Approval gate ---
    try:
        gate_result = await gate.evaluate(approval_req)
    except ApprovalError as exc:
        logger.error("Approval gate error for tool={}: {}", tool_name, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "approval_error",
                "detail": str(exc),
                "correlation_id": body.correlation_id,
            },
        )

    # --- Audit trail ---
    audit_record = AuditRecord(
        agent_id=tool.agent_id,
        tool_name=tool_name,
        risk_level=tool.risk_level,
        outcome=gate_result.outcome.value,
        reason=gate_result.reason,
        parameters=body.parameters,
        correlation_id=body.correlation_id,
        flagged_for_summary=gate_result.flagged_for_summary,
    )
    try:
        await trail.insert(audit_record)
    except AuditError as exc:
        logger.error("Audit trail write failed for tool={}: {}", tool_name, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "audit_error",
                "detail": str(exc),
                "correlation_id": body.correlation_id,
            },
        )

    # --- Response ---
    if gate_result.outcome == ApprovalOutcome.DENIED:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tool_denied",
                "detail": gate_result.reason,
                "correlation_id": body.correlation_id,
            },
        )

    # APPROVED: medium-risk tools are flagged for the daily summary → "queued"
    status = "queued" if gate_result.flagged_for_summary else "ok"
    return InvokeResponse(
        tool_name=tool_name,
        status=status,
        message=gate_result.reason,
    )


# ---------------------------------------------------------------------------
# WebSocket bridge (OpenClaw → OsMEN-OC)
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def openclaw_bridge(websocket: WebSocket) -> None:
    """WebSocket endpoint for OpenClaw control-plane messages.

    Listens on ``ws://127.0.0.1:18789/ws``.
    """
    await websocket.accept()
    logger.info("OpenClaw bridge connected: {}", websocket.client)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Bridge received: {}", data)
            # TODO: parse EventEnvelope and dispatch to event bus
            await websocket.send_text(f'{{"ack": true, "echo": {data!r}}}')
    except WebSocketDisconnect:
        logger.info("OpenClaw bridge disconnected.")
