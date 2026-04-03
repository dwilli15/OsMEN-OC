"""FastAPI application for OsMEN-OC gateway.

Responsibilities
----------------
- Expose ``/health`` liveness probe.
- Expose ``/mcp/tools`` — list all registered MCP tools.
- Expose ``/mcp/tools/{tool_name}/invoke`` — invoke a tool (stubbed).
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

from core.gateway.deps import MCPRegistry
from core.gateway.mcp import MCPTool, register_tools, scan_manifests

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
# MCP tool invocation (stubbed)
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
) -> InvokeResponse:
    """Invoke a registered MCP tool by name (stub — approval gate wired in future PR).

    Returns ``202 Accepted`` with ``status="queued"`` for medium/high/critical risk tools,
    and ``200 OK`` with ``status="ok"`` for low-risk tools.
    """
    tool: MCPTool | None = registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name!r} not registered")

    logger.info(
        "Tool invocation: {} (risk={}, correlation_id={})",
        tool_name,
        tool.risk_level,
        body.correlation_id,
    )

    if tool.risk_level in {"medium", "high", "critical"}:
        return InvokeResponse(
            tool_name=tool_name,
            status="queued",
            message=f"Tool queued for approval (risk_level={tool.risk_level})",
        )

    return InvokeResponse(
        tool_name=tool_name,
        status="ok",
        message="Tool executed (stub — no implementation yet)",
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
