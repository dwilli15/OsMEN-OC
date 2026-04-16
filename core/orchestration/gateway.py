"""Gateway integration — lifecycle hooks for orchestration in the FastAPI app.

Provides:

- ``init_orchestration(app)``: Called during gateway startup to
  initialise the agent registry, compute router, session classifier,
  engines, and bridge adapter.
- ``shutdown_orchestration(app)``: Graceful shutdown of active workflows.
- ``orchestration_health()``: Health check for orchestration subsystem.
- ``get_orchestration_components(app)``: Accessor for orchestration objects.

These are designed to be wired into ``core/gateway/app.py``'s lifespan
context manager.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from core.orchestration.bridge_adapter import BridgeAdapter
from core.orchestration.discussion import DiscussionEngine
from core.orchestration.ledger import Ledger
from core.orchestration.registry import AgentRegistry
from core.orchestration.router import ComputeRouter
from core.orchestration.session import SessionClassifier
from core.orchestration.workflow import CooperativeEngine


async def init_orchestration(app: Any) -> None:
    """Initialise all orchestration components and attach to ``app.state``.

    This is idempotent — calling it multiple times is safe.
    """
    if getattr(app.state, "orchestration_initialised", False):
        return

    # 1. Agent registry
    registry = AgentRegistry()
    agents_dir = getattr(app.state, "agents_dir", "agents")
    registry.load_manifests(agents_dir)
    app.state.agent_registry = registry

    # 2. Compute router
    router = ComputeRouter()
    app.state.compute_router = router

    # 3. Ledger (requires pg_pool from gateway deps)
    pg_pool = getattr(app.state, "pg_pool", None)
    if pg_pool is None:
        logger.warning(
            "orchestration: pg_pool not available on app.state — "
            "orchestration ledger will be non-functional"
        )
        app.state.orchestration_initialised = True
        return

    ledger = Ledger(pg_pool)
    app.state.orchestration_ledger = ledger

    # 4. Session classifier
    classifier = SessionClassifier(ledger)
    app.state.session_classifier = classifier

    # 5. Cooperative engine (Mode A)
    cooperative = CooperativeEngine(ledger)
    app.state.cooperative_engine = cooperative

    # 6. Discussion engine (Mode B)
    discussion = DiscussionEngine(ledger)
    app.state.discussion_engine = discussion

    # 7. Bridge adapter
    adapter = BridgeAdapter(classifier, cooperative, discussion)
    app.state.bridge_adapter = adapter

    # 8. Wire bridge message handler to use adapter
    bridge_client = getattr(app.state, "bridge_client", None)
    if bridge_client is not None:
        _orig_handler = getattr(app.state, "_bridge_message_handler", None)

        async def _orchestration_bridge_handler(msg: Any) -> None:
            from core.bridge.protocol import BridgeInboundMessage

            inbound = BridgeInboundMessage(**msg) if isinstance(msg, dict) else msg
            event = await adapter.handle_message(inbound)
            # Also call the original handler for event bus publishing
            if _orig_handler:
                await _orig_handler(inbound)

        bridge_client.on_message = _orchestration_bridge_handler
        logger.info("orchestration: bridge adapter wired to bridge client")

    app.state.orchestration_initialised = True
    logger.info(
        "orchestration: initialised (agents={}, tiers={})",
        len(registry.agent_ids),
        len(router.available_tiers),
    )


async def shutdown_orchestration(app: Any) -> None:
    """Gracefully shut down active workflows."""
    cooperative = getattr(app.state, "cooperative_engine", None)
    discussion = getattr(app.state, "discussion_engine", None)

    if cooperative:
        # Cancel all active cooperative workflows
        active = getattr(cooperative, "_active_workflows", {})
        for wf_id in list(active.keys()):
            logger.info("orchestration: cancelling workflow {}", wf_id)
            await cooperative.cancel_workflow(wf_id)

    if discussion:
        active = getattr(discussion, "_active", {})
        for wf_id in list(active.keys()):
            logger.info("orchestration: cancelling discussion {}", wf_id)
            await discussion.cancel_discussion(wf_id)

    logger.info("orchestration: shutdown complete")


def orchestration_health(app: Any) -> dict[str, Any]:
    """Return health status of orchestration components."""
    components: dict[str, Any] = {}

    registry = getattr(app.state, "agent_registry", None)
    components["registry"] = {
        "status": "ok" if registry else "not_initialised",
        "agent_count": len(registry.agent_ids) if registry else 0,
    }

    router = getattr(app.state, "compute_router", None)
    components["compute_router"] = {
        "status": "ok" if router else "not_initialised",
        "tiers": router.available_tiers if router else [],
    }

    ledger = getattr(app.state, "orchestration_ledger", None)
    components["ledger"] = {
        "status": "ok" if ledger else "not_available",
        "reason": "no_pg_pool" if not ledger else None,
    }

    cooperative = getattr(app.state, "cooperative_engine", None)
    active_wf = len(getattr(cooperative, "_active_workflows", {})) if cooperative else 0
    components["cooperative_engine"] = {
        "status": "ok" if cooperative else "not_initialised",
        "active_workflows": active_wf,
    }

    discussion = getattr(app.state, "discussion_engine", None)
    active_disc = len(getattr(discussion, "_active", {})) if discussion else 0
    components["discussion_engine"] = {
        "status": "ok" if discussion else "not_initialised",
        "active_discussions": active_disc,
    }

    return components


def get_orchestration_components(app: Any) -> dict[str, Any]:
    """Retrieve all orchestration components from app.state."""
    return {
        "registry": getattr(app.state, "agent_registry", None),
        "router": getattr(app.state, "compute_router", None),
        "ledger": getattr(app.state, "orchestration_ledger", None),
        "classifier": getattr(app.state, "session_classifier", None),
        "cooperative_engine": getattr(app.state, "cooperative_engine", None),
        "discussion_engine": getattr(app.state, "discussion_engine", None),
        "bridge_adapter": getattr(app.state, "bridge_adapter", None),
    }
