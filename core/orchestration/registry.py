"""Agent identity registry.

Loads YAML manifests from ``agents/*.yaml`` and provides lookups by
agent_id, capability, or conversation group.  The registry is the
single source of truth for which agents exist, what they can do, and
who they're allowed to talk to.

Key concepts:

- **Agent identity**: An agent_id (e.g. ``"research"``) plus its
  manifest metadata (name, capabilities, tools, risk levels).
- **allowFrom**: An optional ACL that restricts which agents or
  channels can trigger this agent.  If empty, the agent accepts
  requests from any source.
- **Conversation groups**: Multiple agents can be grouped for
  multi-agent discussion workflows (Mode B orchestration).

Usage::

    registry = AgentRegistry()
    registry.load_manifests("agents/")

    agent = registry.get("research")
    agents = registry.find_by_capability("web-research")
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


@dataclass
class ToolSpec:
    """Specification for a single tool exposed by an agent."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"


@dataclass
class AgentIdentity:
    """Resolved identity for a registered agent."""

    agent_id: str
    name: str
    model_tier: str
    capabilities: list[str] = field(default_factory=list)
    description: str = ""
    tools: list[ToolSpec] = field(default_factory=list)
    allow_from: list[str] = field(default_factory=list)
    conversation_group: str | None = None
    manifest_hash: str = ""
    raw_manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self.tools]

    @property
    def high_risk_tools(self) -> list[ToolSpec]:
        return [t for t in self.tools if t.risk_level in ("high", "critical")]


class AgentRegistry:
    """Registry of agent identities loaded from YAML manifests.

    Thread-safe for reads after initial load.  Call
    :meth:`load_manifests` once at startup.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentIdentity] = {}

    @property
    def agent_ids(self) -> list[str]:
        """Return all registered agent IDs."""
        return list(self._agents.keys())

    def load_manifests(self, agents_dir: str | Path) -> int:
        """Scan ``agents_dir`` for ``*.yaml`` manifests and register each.

        Args:
            agents_dir: Directory containing agent YAML manifests.

        Returns:
            Number of agents successfully loaded.
        """
        agents_dir = Path(agents_dir)
        if not agents_dir.is_dir():
            logger.warning("Agent manifests directory not found: {}", agents_dir)
            return 0

        count = 0
        for manifest_path in sorted(agents_dir.glob("*.yaml")):
            try:
                if self._load_one(manifest_path):
                    count += 1
            except Exception as exc:
                logger.error(
                    "Failed to load agent manifest {}: {}",
                    manifest_path,
                    exc,
                )
        logger.info("Agent registry: loaded {} agents from {}", count, agents_dir)
        return count

    def get(self, agent_id: str) -> AgentIdentity | None:
        """Look up an agent by ID.  Returns None if not registered."""
        return self._agents.get(agent_id)

    def find_by_capability(self, capability: str) -> list[AgentIdentity]:
        """Return agents that declare *capability* in their manifest."""
        return [
            a
            for a in self._agents.values()
            if capability in a.capabilities
        ]

    def find_by_conversation_group(self, group: str) -> list[AgentIdentity]:
        """Return all agents in a conversation group."""
        return [
            a
            for a in self._agents.values()
            if a.conversation_group == group
        ]

    def find_by_model_tier(self, tier: str) -> list[AgentIdentity]:
        """Return agents matching a model tier (exact match)."""
        return [a for a in self._agents.values() if a.model_tier == tier]

    def is_allowed(
        self,
        agent_id: str,
        source_agent_id: str | None = None,
        source_channel: str | None = None,
    ) -> bool:
        """Check whether *source* is allowed to invoke *agent_id*.

        If the target agent has no ``allowFrom`` rules, any source is
        permitted.

        Args:
            agent_id: The agent being invoked.
            source_agent_id: The invoking agent (if another agent).
            source_channel: The invoking channel (if from bridge/event).

        Returns:
            True if the invocation is permitted.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        if not agent.allow_from:
            return True

        if source_agent_id and source_agent_id in agent.allow_from:
            return True
        if source_channel and source_channel in agent.allow_from:
            return True
        return False

    def get_tools_for_agent(self, agent_id: str) -> list[ToolSpec]:
        """Return the tool list for a registered agent, or empty list."""
        agent = self._agents.get(agent_id)
        return agent.tools if agent else []

    def summary(self) -> dict[str, Any]:
        """Return a serialisable summary of all registered agents."""
        return {
            agent_id: {
                "name": a.name,
                "model_tier": a.model_tier,
                "capabilities": a.capabilities,
                "tool_count": len(a.tools),
                "conversation_group": a.conversation_group,
            }
            for agent_id, a in self._agents.items()
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _load_one(self, path: Path) -> bool:
        """Load and register a single YAML manifest.

        Returns:
            True if the agent was registered, False if skipped.
        """
        raw = path.read_text(encoding="utf-8")
        manifest = yaml.safe_load(raw)
        if not isinstance(manifest, dict) or "agent_id" not in manifest:
            logger.warning("Skipping invalid manifest: {}", path)
            return False

        agent_id = manifest["agent_id"]
        manifest_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        tools = [
            ToolSpec(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
                risk_level=t.get("risk_level", "low"),
            )
            for t in manifest.get("tools", [])
        ]

        identity = AgentIdentity(
            agent_id=agent_id,
            name=manifest.get("name", agent_id),
            model_tier=manifest.get("model_tier", "local-small"),
            capabilities=manifest.get("capabilities", []),
            description=manifest.get("description", ""),
            tools=tools,
            allow_from=manifest.get("allowFrom", []),
            conversation_group=manifest.get("conversation_group"),
            manifest_hash=manifest_hash,
            raw_manifest=manifest,
        )

        self._agents[agent_id] = identity
        logger.debug(
            "Registered agent {} (tier={}, tools={}, caps={})",
            agent_id,
            identity.model_tier,
            len(tools),
            len(identity.capabilities),
        )
        return True
