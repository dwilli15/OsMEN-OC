# Agent Loading Architecture

## Authority

The **authoritative** source for agent definitions is `agents/*.yaml` (individual YAML manifests).

The `config/agents.yaml` file is a **reference/overview** document — it is NOT read by the gateway at runtime.

## Loading Flow

1. Gateway starts → reads `OSMEN_AGENTS_DIR` env var (default: `agents/`)
2. `scan_manifests(agents_dir)` scans all `*.yaml` files in that directory
3. Each manifest's `tools` section is registered in the MCP tool registry
4. The `register_tools()` function creates `MCPTool` objects with handler references

## Adding a New Agent

1. Create `agents/new_agent.yaml` with the standard manifest format
2. Implement tool handlers in `core/gateway/builtin_handlers.py` (decorated with `@register_handler`)
3. Restart the gateway — the new agent's tools will be auto-registered
