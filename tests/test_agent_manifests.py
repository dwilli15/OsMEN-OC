"""Tests for agent manifest parsing and MCP tool registration.

Covers:
- All ``agents/*.yaml`` files parse without errors.
- Each manifest has required fields (agent_id, name, model_tier, tools).
- All tools have valid risk_level values.
- ``scan_manifests`` returns tools from every manifest.
- ``register_tools`` raises RegistrationError on duplicate tool names.
- ``config/agents.yaml`` and ``config/pipelines.yaml`` parse without errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.gateway.mcp import (
    VALID_RISK_LEVELS,
    AgentManifest,
    MCPTool,
    register_tools,
    scan_manifests,
)
from core.utils.config import load_config
from core.utils.exceptions import ManifestError, RegistrationError

REPO_ROOT = Path(__file__).parent.parent
AGENTS_DIR = REPO_ROOT / "agents"
CONFIG_DIR = REPO_ROOT / "config"

EXPECTED_AGENT_IDS = {
    "daily_brief",
    "knowledge_librarian",
    "media_organization",
    "boot_hardening",
    "focus_guardrails",
    "taskwarrior_sync",
    "system_monitor",
    "research",
}

# ---------------------------------------------------------------------------
# Discover manifest files for parametrised tests
# ---------------------------------------------------------------------------

_manifest_files = sorted(AGENTS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("manifest_path", _manifest_files, ids=lambda p: p.stem)
def test_manifest_is_valid_yaml(manifest_path: Path) -> None:
    """Each agent manifest must be parseable as YAML."""
    data = yaml.safe_load(manifest_path.read_text())
    assert isinstance(data, dict), f"{manifest_path.name} must be a YAML mapping"


@pytest.mark.parametrize("manifest_path", _manifest_files, ids=lambda p: p.stem)
def test_manifest_required_fields(manifest_path: Path) -> None:
    """Each manifest must contain agent_id, name, model_tier, and tools."""
    data = yaml.safe_load(manifest_path.read_text())
    for field in ("agent_id", "name", "model_tier", "tools"):
        assert field in data, f"{manifest_path.name} is missing field '{field}'"


@pytest.mark.parametrize("manifest_path", _manifest_files, ids=lambda p: p.stem)
def test_manifest_passes_pydantic_validation(manifest_path: Path) -> None:
    """Each manifest must validate against AgentManifest schema."""
    data = yaml.safe_load(manifest_path.read_text())
    # Should not raise
    manifest = AgentManifest(**data)
    assert manifest.agent_id
    assert manifest.model_tier


@pytest.mark.parametrize("manifest_path", _manifest_files, ids=lambda p: p.stem)
def test_manifest_tool_risk_levels_are_valid(manifest_path: Path) -> None:
    """Every tool in each manifest must declare a valid risk_level."""
    data = yaml.safe_load(manifest_path.read_text())
    for tool in data.get("tools", []):
        risk = tool.get("risk_level", "low")
        assert risk in VALID_RISK_LEVELS, (
            f"{manifest_path.name}: tool {tool.get('name')!r} has invalid risk_level {risk!r}"
        )


# ---------------------------------------------------------------------------
# scan_manifests
# ---------------------------------------------------------------------------


def test_scan_manifests_returns_tools() -> None:
    """scan_manifests must return at least one tool per manifest file."""
    tools = scan_manifests(AGENTS_DIR)
    assert len(tools) > 0
    for tool in tools:
        assert isinstance(tool, MCPTool)


def test_scan_manifests_covers_all_agents() -> None:
    """scan_manifests must produce tools from every expected agent."""
    tools = scan_manifests(AGENTS_DIR)
    agent_ids = {t.agent_id for t in tools}
    assert EXPECTED_AGENT_IDS.issubset(agent_ids), (
        f"Missing agent IDs: {EXPECTED_AGENT_IDS - agent_ids}"
    )


def test_scan_manifests_empty_dir(tmp_path: Path) -> None:
    """scan_manifests on an empty directory must return an empty list."""
    result = scan_manifests(tmp_path)
    assert result == []


def test_scan_manifests_invalid_yaml_raises(tmp_path: Path) -> None:
    """scan_manifests must raise ManifestError for unparseable YAML."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("agent_id: [unclosed", encoding="utf-8")
    with pytest.raises(ManifestError):
        scan_manifests(tmp_path)


def test_scan_manifests_missing_field_raises(tmp_path: Path) -> None:
    """scan_manifests must raise ManifestError when a required field is absent."""
    incomplete = tmp_path / "incomplete.yaml"
    incomplete.write_text(
        "agent_id: test\nname: Test\n# model_tier is missing\ntools: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        scan_manifests(tmp_path)


# ---------------------------------------------------------------------------
# register_tools
# ---------------------------------------------------------------------------


def test_register_tools_builds_name_keyed_dict() -> None:
    """register_tools must return a dict keyed by tool name."""
    tools = [
        MCPTool(agent_id="a1", name="tool_one", risk_level="low"),
        MCPTool(agent_id="a2", name="tool_two", risk_level="medium"),
    ]
    registry = register_tools(tools)
    assert set(registry.keys()) == {"tool_one", "tool_two"}


def test_register_tools_duplicate_raises() -> None:
    """register_tools must raise RegistrationError on duplicate tool names."""
    tools = [
        MCPTool(agent_id="agent_a", name="dup_tool", risk_level="low"),
        MCPTool(agent_id="agent_b", name="dup_tool", risk_level="low"),
    ]
    with pytest.raises(RegistrationError):
        register_tools(tools)


def test_register_tools_empty_list() -> None:
    """register_tools on an empty list must return an empty dict."""
    assert register_tools([]) == {}


# ---------------------------------------------------------------------------
# Config file validation
# ---------------------------------------------------------------------------


def test_agents_config_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """config/agents.yaml must load without errors."""
    # Provide placeholder values for env vars referenced in agents.yaml
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setenv("PLEX_LIBRARY_ROOT", "/tmp/plex")
    monkeypatch.setenv("DOWNLOAD_STAGING_DIR", "/tmp/staging")
    monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "/tmp/gcal-creds.json")
    config = load_config(CONFIG_DIR / "agents.yaml")
    assert "defaults" in config


def test_pipelines_config_parses() -> None:
    """config/pipelines.yaml must load without errors."""
    config = load_config(CONFIG_DIR / "pipelines.yaml")
    assert "pipelines" in config
    assert isinstance(config["pipelines"], list)
    assert len(config["pipelines"]) > 0


def test_pipelines_reference_known_agents() -> None:
    """Every pipeline step must reference an agent_id present in agents/."""
    config = load_config(CONFIG_DIR / "pipelines.yaml")
    known_ids = {p.stem for p in AGENTS_DIR.glob("*.yaml")}
    for pipeline in config["pipelines"]:
        for step in pipeline.get("steps", []):
            assert step["agent"] in known_ids, (
                f"Pipeline {pipeline['id']!r} references unknown agent {step['agent']!r}"
            )


# ---------------------------------------------------------------------------
# Async smoke test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scan_manifests_async_wrapper() -> None:
    """scan_manifests can be called from async context without blocking issues."""
    import anyio

    tools = await anyio.to_thread.run_sync(lambda: scan_manifests(AGENTS_DIR))
    assert len(tools) > 0
