"""FastAPI application for OsMEN-OC gateway.

Responsibilities
----------------
- Expose ``/health`` liveness probe.
- Expose ``/mcp/tools`` — list all registered MCP tools.
- Expose ``/mcp/tools/{tool_name}/invoke`` — invoke a tool through the
  :class:`~core.approval.gate.ApprovalGate` and persist the result via
  :class:`~core.audit.trail.AuditTrail`.
- At startup: scan ``agents/*.yaml`` and populate the MCP tool registry.
- At startup: connect Redis → EventBus, asyncpg → pg_pool when env vars present.
- At startup: launch OpenClaw bridge client as a background task when configured.
- Accept WebSocket connections from OpenClaw at ``ws://127.0.0.1:18789``.
"""

from __future__ import annotations

import asyncio
import json as _json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

# Import builtin handlers so they register on the global handler_registry
import core.gateway.builtin_handlers as _builtin_handlers  # noqa: F401
from core.approval.gate import ApprovalGate, ApprovalOutcome, ApprovalRequest, RiskLevel
from core.audit.trail import AuditRecord
from core.bridge.protocol import BridgeInboundMessage, BridgeOutboundMessage
from core.events.envelope import EventEnvelope, EventPriority
from core.gateway.deps import ApprovalGateDep, AuditTrailDep, EventBusDep, MCPRegistry
from core.gateway.handlers import HandlerContext, handler_registry
from core.gateway.mcp import MCPTool, register_tools, scan_manifests
from core.utils.exceptions import ApprovalError, AuditError, EventBusError

# ---------------------------------------------------------------------------
# Optional runtime imports (graceful fallback when not installed)
# ---------------------------------------------------------------------------


def _try_import_redis():
    """Lazily import redis.asyncio; return None when the package is absent."""
    try:
        import redis.asyncio as aioredis

        return aioredis
    except ImportError:
        return None


def _try_import_asyncpg():
    """Lazily import asyncpg; return None when the package is absent."""
    try:
        import asyncpg

        return asyncpg
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Bridge message handler (used by OpenClawBridgeClient)
# ---------------------------------------------------------------------------


async def _bridge_message_handler(app_ref: FastAPI, msg: BridgeInboundMessage) -> None:
    """Dispatch an inbound bridge message onto the event bus."""
    event_bus = getattr(app_ref.state, "event_bus", None)
    if event_bus is None:
        logger.warning("Bridge message received but no event bus configured, dropping")
        return

    envelope = EventEnvelope(
        domain="bridge",
        category=msg.type,
        source="openclaw",
        correlation_id=msg.correlation_id,
        priority=EventPriority.NORMAL,
        payload=msg.payload,
    )
    try:
        await event_bus.publish(envelope)
        logger.debug("Bridge message dispatched: type={} cid={}", msg.type, msg.correlation_id)
    except EventBusError as exc:
        logger.error("Bridge dispatch failed: {}", exc)


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

    # --- Approval gate (always available) ---
    app.state.approval_gate = ApprovalGate()

    # --- Redis → EventBus (optional) ---
    redis_url = os.environ.get("REDIS_URL")
    redis_client = None
    aioredis = _try_import_redis()
    if redis_url and aioredis is not None:
        try:
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            from core.events.bus import EventBus

            app.state.event_bus = EventBus(redis_client)
            logger.info("EventBus connected to Redis at {}", redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed ({}), event bus in noop mode", exc)
            redis_client = None
    else:
        if redis_url and aioredis is None:
            logger.warning("REDIS_URL set but redis package not installed")
        logger.info("EventBus running in noop mode (REDIS_URL not configured)")

    # --- asyncpg pool (optional) ---
    pg_pool = None
    asyncpg = _try_import_asyncpg()
    database_url = os.environ.get("DATABASE_URL")
    if database_url and asyncpg is not None:
        try:
            pg_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
            app.state.pg_pool = pg_pool
            logger.info("PostgreSQL pool connected to {}", database_url.split("@")[-1])
        except Exception as exc:
            logger.warning("PostgreSQL connection failed ({}), audit trail unavailable", exc)
            pg_pool = None
    else:
        if database_url and asyncpg is None:
            logger.warning("DATABASE_URL set but asyncpg package not installed")
        logger.info("PostgreSQL pool not configured (DATABASE_URL not set)")

    # --- OpenClaw bridge client (optional background task) ---
    bridge_task = None
    bridge_url = os.environ.get("OPENCLAW_WS_URL")
    if bridge_url:
        from core.bridge.ws_client import OpenClawBridgeClient

        bridge_client = OpenClawBridgeClient(
            endpoint=bridge_url,
            on_message=lambda msg: _bridge_message_handler(app, msg),
        )
        app.state.bridge_client = bridge_client
        bridge_task = asyncio.create_task(bridge_client.run_forever())
        logger.info("OpenClaw bridge client started → {}", bridge_url)

    # --- Pipeline runner (optional, requires event bus) ---
    pipeline_runner = None
    if hasattr(app.state, "event_bus"):
        try:
            from core.pipelines.runner import PipelineRunner

            pipeline_runner = PipelineRunner(
                event_bus=app.state.event_bus,
                mcp_registry=app.state.mcp_registry,
                approval_gate=app.state.approval_gate,
                audit_trail_pool=pg_pool,
                app_state=app.state,
            )
            await pipeline_runner.start()
            app.state.pipeline_runner = pipeline_runner
            logger.info("Pipeline runner started with {} pipelines", len(pipeline_runner.pipelines))
        except Exception as exc:
            logger.warning("Pipeline runner failed to start: {}", exc)

    yield

    # --- Shutdown ---
    if pipeline_runner is not None:
        await pipeline_runner.stop()
        logger.info("Pipeline runner stopped")

    if bridge_task is not None:
        bridge_task.cancel()
        try:
            await bridge_task
        except asyncio.CancelledError:
            pass
        logger.info("OpenClaw bridge client stopped")

    if pg_pool is not None:
        await pg_pool.close()
        logger.info("PostgreSQL pool closed")

    if redis_client is not None:
        await redis_client.close()
        logger.info("Redis connection closed")

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
    event_bus: EventBusDep,
) -> InvokeResponse:
    """Invoke a registered MCP tool by name.

    Every invocation is evaluated through the :class:`~core.approval.gate.ApprovalGate`
    before a result is returned, an :class:`~core.audit.trail.AuditRecord` is
    written via the injected :class:`~core.audit.trail.AuditTrail`, and approved
    invocations emit an :class:`~core.events.envelope.EventEnvelope` onto the event bus.

    Returns:
        - ``200 OK`` with ``status="ok"`` for approved low-risk tools.
        - ``200 OK`` with ``status="queued"`` for approved tools flagged for
          the daily summary (medium-risk).
        - ``403 Forbidden`` with a structured JSON error body when the gate
          denies the request (high/critical risk without a configured approval
          callback, or explicit human denial).
        - ``500 Internal Server Error`` with a structured JSON error body when
          the approval gate or audit trail raise an unexpected error.
        - ``500 Internal Server Error`` when event publication fails.
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

    priority_map = {
        "low": EventPriority.LOW,
        "medium": EventPriority.NORMAL,
        "high": EventPriority.HIGH,
        "critical": EventPriority.CRITICAL,
    }
    event = EventEnvelope(
        domain="tools",
        category="invocation",
        source=tool.agent_id,
        correlation_id=body.correlation_id,
        priority=priority_map.get(tool.risk_level, EventPriority.NORMAL),
        payload={
            "tool_name": tool_name,
            "agent_id": tool.agent_id,
            "risk_level": tool.risk_level,
            "outcome": gate_result.outcome.value,
            "flagged_for_summary": gate_result.flagged_for_summary,
            "parameters": body.parameters,
            "correlation_id": body.correlation_id,
        },
    )
    try:
        await event_bus.publish(event)
    except EventBusError as exc:
        logger.error("Event bus publish failed for tool={}: {}", tool_name, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "event_bus_error",
                "detail": str(exc),
                "correlation_id": body.correlation_id,
            },
        )

    # APPROVED: execute handler if one is registered
    handler_result: Any = None
    if handler_registry.has(tool_name):
        ctx = HandlerContext(
            agent_id=tool.agent_id,
            correlation_id=body.correlation_id,
            app_state=getattr(app, "state", None),
        )
        try:
            handler_result = await handler_registry.execute(tool_name, body.parameters, ctx)
        except Exception as exc:
            logger.error("Handler execution failed for tool={}: {}", tool_name, exc)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "handler_error",
                    "detail": str(exc),
                    "tool_name": tool_name,
                    "correlation_id": body.correlation_id,
                },
            )

    # APPROVED: medium-risk tools are flagged for the daily summary → "queued"
    status = "queued" if gate_result.flagged_for_summary else "ok"
    return InvokeResponse(
        tool_name=tool_name,
        status=status,
        result=handler_result,
        message=gate_result.reason,
    )


# ---------------------------------------------------------------------------
# WebSocket bridge (OpenClaw → OsMEN-OC)
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def openclaw_bridge(websocket: WebSocket) -> None:
    """WebSocket endpoint for OpenClaw control-plane messages.

    Listens on ``ws://127.0.0.1:18789/ws``.  Parses each frame as a
    :class:`~core.bridge.protocol.BridgeInboundMessage`, dispatches it
    as an :class:`~core.events.envelope.EventEnvelope` on the event bus,
    and sends an acknowledgment back.
    """
    await websocket.accept()
    logger.info("OpenClaw bridge connected: {}", websocket.client)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Bridge received: {}", data)
            try:
                msg = BridgeInboundMessage.model_validate_json(data)
            except Exception as exc:
                logger.warning("Bridge message parse error: {}", exc)
                await websocket.send_text(_json.dumps({"ack": False, "error": str(exc)}))
                continue

            await _bridge_message_handler(app, msg)

            ack = BridgeOutboundMessage(
                type="ack",
                correlation_id=msg.correlation_id,
                payload={"received_type": msg.type},
            )
            await websocket.send_text(ack.model_dump_json())
    except WebSocketDisconnect:
        logger.info("OpenClaw bridge disconnected.")
