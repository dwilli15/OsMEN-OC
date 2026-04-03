"""Agent manifest scanner and MCP tool registration.

At gateway startup, :func:`scan_manifests` reads every ``agents/*.yaml`` file,
validates it against :class:`AgentManifest`, and returns a flat list of
:class:`MCPTool` objects ready to be registered as FastAPI endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from core.utils.exceptions import ManifestError, RegistrationError

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

VALID_MODEL_TIERS = {"cloud-primary", "local-medium", "local-small", "haiku"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


class ToolParameter(BaseModel):
    type: str
    required: bool = False
    description: str = ""
    enum: list[str] | None = None


class MCPTool(BaseModel):
    """A single tool exposed via the MCP endpoint."""

    agent_id: str
    name: str
    description: str = ""
    parameters: dict[str, ToolParameter] = Field(default_factory=dict)
    risk_level: str = "low"

    @field_validator("risk_level")
    @classmethod
    def _validate_risk(cls, v: str) -> str:
        if v not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {VALID_RISK_LEVELS}, got {v!r}")
        return v


class AgentManifest(BaseModel):
    """Schema for an agent YAML manifest file."""

    agent_id: str
    name: str
    model_tier: str
    capabilities: list[str] = Field(default_factory=list)
    description: str = ""
    tools: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("model_tier")
    @classmethod
    def _validate_tier(cls, v: str) -> str:
        if v not in VALID_MODEL_TIERS:
            raise ValueError(f"model_tier must be one of {VALID_MODEL_TIERS}, got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _parse_tool(agent_id: str, raw: dict[str, Any]) -> MCPTool:
    """Parse a single tool dict from an agent manifest into an MCPTool."""
    try:
        params: dict[str, ToolParameter] = {}
        for param_name, param_data in raw.get("parameters", {}).items():
            params[param_name] = ToolParameter(**param_data)

        return MCPTool(
            agent_id=agent_id,
            name=raw["name"],
            description=raw.get("description", ""),
            parameters=params,
            risk_level=raw.get("risk_level", "low"),
        )
    except (KeyError, ValueError) as exc:
        raise ManifestError(
            f"Invalid tool definition in agent {agent_id!r}: {exc}"
        ) from exc


def scan_manifests(agents_dir: str | Path = "agents") -> list[MCPTool]:
    """Scan all YAML manifests in *agents_dir* and return their tools.

    Args:
        agents_dir: Directory containing ``*.yaml`` agent manifests.

    Returns:
        Flat list of :class:`MCPTool` objects across all manifests.

    Raises:
        ManifestError: If any manifest is malformed or missing required fields.
    """
    agents_path = Path(agents_dir)
    if not agents_path.is_absolute():
        agents_path = Path.cwd() / agents_path

    yaml_files = sorted(agents_path.glob("*.yaml"))
    if not yaml_files:
        logger.warning("No agent manifests found in {}", agents_path)
        return []

    tools: list[MCPTool] = []

    for manifest_file in yaml_files:
        try:
            raw = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ManifestError(f"Cannot parse manifest {manifest_file}: {exc}") from exc

        try:
            manifest = AgentManifest(**raw)
        except Exception as exc:
            raise ManifestError(
                f"Manifest validation failed for {manifest_file.name}: {exc}"
            ) from exc

        logger.info(
            "Loaded agent manifest: {} ({} tools)", manifest.agent_id, len(manifest.tools)
        )

        for tool_raw in manifest.tools:
            tools.append(_parse_tool(manifest.agent_id, tool_raw))

    return tools


def register_tools(tools: list[MCPTool]) -> dict[str, MCPTool]:
    """Build a name-keyed registry from a list of MCP tools.

    Args:
        tools: Tools produced by :func:`scan_manifests`.

    Returns:
        Mapping of ``tool_name`` → :class:`MCPTool`.

    Raises:
        RegistrationError: If two tools share the same name across agents.
    """
    registry: dict[str, MCPTool] = {}
    for tool in tools:
        if tool.name in registry:
            raise RegistrationError(
                f"Duplicate tool name {tool.name!r}: claimed by both "
                f"{registry[tool.name].agent_id!r} and {tool.agent_id!r}"
            )
        registry[tool.name] = tool

    logger.info("MCP registry: {} tools registered", len(registry))
    return registry
