"""Compute router — resolves task requirements to concrete inference
endpoints using the compute-routing configuration.

The router reads ``config/compute-routing.yaml`` and selects the best
available backend for a given task type, model size, and capability tier.

Responsibilities:

- Match task requirements to :data:`backend_tiers` entries.
- Resolve provider endpoints from the :data:`providers` map.
- Enforce NPU hot-model policy (single loaded model, LRU warm priority).
- Provide fallback chains when the preferred backend is unavailable.

Usage::

    router = ComputeRouter(config)
    endpoint = await router.resolve(
        task_type="inference",
        model_size_gb=4,
        capability_tier="medium",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from core.utils.config import load_config


@dataclass
class ProviderEndpoint:
    """A resolved inference provider endpoint."""

    name: str  # e.g. "ollama", "lemonade", "cloud_zai"
    base_url: str
    api_style: str  # "ollama" or "openai"
    compute: str  # "nvidia", "npu", "amd_vulkan", "cpu", "cloud"
    backend_recipe: str | None = None  # e.g. "llamacpp", "flm", "kokoro"


@dataclass
class RoutingDecision:
    """Result of a routing computation."""

    provider: ProviderEndpoint
    model_id: str
    tier: str  # "swarm_local_fast", "worker_local_medium", etc.
    fallback_chain: list[ProviderEndpoint] = field(default_factory=list)
    model_size_gb: float | None = None
    model_params: str | None = None
    confidence: float = 1.0


class ComputeRouter:
    """Resolves task requirements to inference endpoints.

    Args:
        config: Loaded compute-routing config dict.  If None, loads
            from ``config/compute-routing.yaml``.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            try:
                from core.utils.config import load_config
                full_cfg = load_config("config/compute-routing.yaml")
                config = full_cfg.get("compute_routing", {})
            except Exception:
                config = {}
        self._config = config
        self._providers: dict[str, ProviderEndpoint] = {}
        self._backend_tiers: dict[str, dict[str, Any]] = {}
        self._npu_policy: dict[str, Any] = {}
        self._rules: list[dict[str, Any]] = []
        self._default_compute: str = "cpu"
        self._npu_hot_model: str | None = None
        self._npu_warm_priority: list[str] = []

        self._parse_config()

    @property
    def providers(self) -> dict[str, ProviderEndpoint]:
        """All resolved provider endpoints."""
        return dict(self._providers)

    @property
    def available_tiers(self) -> list[str]:
        """Names of configured backend tiers."""
        return list(self._backend_tiers.keys())

    # ── Public API ──────────────────────────────────────────────────────────

    async def resolve(
        self,
        *,
        task_type: str = "inference",
        model_size_gb: float | None = None,
        capability_tier: str | None = None,
        preferred_model: str | None = None,
    ) -> RoutingDecision:
        """Select the best backend for the given requirements.

        Resolution order:
        1. If ``preferred_model`` is specified, find its tier and provider.
        2. If ``capability_tier`` matches a backend tier, use that tier.
        3. Fall back to rule-based matching on task_type and model_size_gb.
        4. Final fallback to ``default_compute``.

        Args:
            task_type: The type of workload (inference, embedding, etc.).
            model_size_gb: Model size in GB for routing rules.
            capability_tier: Explicit tier name (e.g. "worker_local_medium").
            preferred_model: Specific model ID to route to.

        Returns:
            A :class:`RoutingDecision` with provider, model, and fallbacks.
        """
        # 1. Preferred model — look it up across all tiers
        if preferred_model:
            decision = self._resolve_preferred_model(preferred_model)
            if decision:
                return decision
            logger.warning(
                "compute: preferred model {} not found in any tier, "
                "falling back to rule-based routing",
                preferred_model,
            )

        # 2. Explicit tier
        if capability_tier and capability_tier in self._backend_tiers:
            return self._resolve_tier(capability_tier)

        # 3. Rule-based matching
        decision = self._resolve_rules(task_type, model_size_gb)
        if decision:
            return decision

        # 4. Default
        logger.debug("compute: using default_compute={}", self._default_compute)
        return RoutingDecision(
            provider=self._providers.get(self._default_compute, self._providers.get("lemonade")),
            model_id="",
            tier="default",
            confidence=0.3,
        )

    def get_npu_hot_model(self) -> str | None:
        """Return the current NPU hot model ID, or None if unknown."""
        return self._npu_hot_model

    def set_npu_hot_model(self, model_id: str) -> None:
        """Update the NPU hot model (called when a model is loaded)."""
        self._npu_hot_model = model_id
        logger.debug("compute: NPU hot model set to {}", model_id)

    def get_endpoint(self, provider_name: str) -> ProviderEndpoint | None:
        """Look up a provider endpoint by name."""
        return self._providers.get(provider_name)

    # ── Internal ────────────────────────────────────────────────────────────

    def _parse_config(self) -> None:
        """Parse the compute-routing config into internal structures."""
        # Default compute
        self._default_compute = self._config.get("default_compute", "cpu")

        # Providers
        for name, p_cfg in self._config.get("providers", {}).items():
            self._providers[name] = ProviderEndpoint(
                name=name,
                base_url=p_cfg.get("base_url", ""),
                api_style=p_cfg.get("api_style", "openai"),
                compute=p_cfg.get("compute", "cpu"),
                backend_recipe=None,
            )

        # Backend tiers
        self._backend_tiers = self._config.get("backend_tiers", {})

        # Rules (sorted by priority descending)
        self._rules = sorted(
            self._config.get("rules", []),
            key=lambda r: r.get("priority", 0),
            reverse=True,
        )

        # NPU policy
        self._npu_policy = self._config.get("npu_policy", {})
        self._npu_warm_priority = self._npu_policy.get("warm_priority", [])
        self._npu_hot_model = self._npu_warm_priority[0] if self._npu_warm_priority else None

    def _resolve_preferred_model(self, model_id: str) -> RoutingDecision | None:
        """Look up a specific model across all backend tiers."""
        for tier_name, tier_cfg in self._backend_tiers.items():
            models = tier_cfg.get("models", [])
            for m in models:
                if m == model_id or (isinstance(m, dict) and m.get("id") == model_id):
                    # Found the model — resolve the provider
                    target = tier_cfg.get("target_compute", "cpu")
                    provider = self._find_provider_by_compute(target)
                    if provider:
                        fallback = self._build_fallback_chain(tier_cfg)
                        return RoutingDecision(
                            provider=provider,
                            model_id=model_id,
                            tier=tier_name,
                            fallback_chain=fallback,
                            confidence=0.95,
                        )
        return None

    def _resolve_tier(self, tier_name: str) -> RoutingDecision:
        """Resolve a backend tier to a concrete endpoint."""
        tier_cfg = self._backend_tiers[tier_name]
        target = tier_cfg.get("target_compute", "cpu")

        # Check NPU policy — prefer warm model
        provider = self._find_provider_by_compute(target)

        # Pick the first model from the tier
        models = tier_cfg.get("models", [])
        model_id = models[0] if models else ""

        fallback = self._build_fallback_chain(tier_cfg)

        return RoutingDecision(
            provider=provider,
            model_id=model_id,
            tier=tier_name,
            fallback_chain=fallback,
            confidence=0.8,
        )

    def _resolve_rules(
        self,
        task_type: str,
        model_size_gb: float | None,
    ) -> RoutingDecision | None:
        """Match against routing rules."""
        for rule in self._rules:
            trigger = rule.get("trigger", {})

            # Check task_type match
            if trigger.get("task_type") and trigger["task_type"] != task_type:
                continue

            # Check model size constraints
            if model_size_gb is not None:
                min_gb = trigger.get("model_size_gb_min")
                max_gb = trigger.get("model_size_gb_max")
                if min_gb is not None and model_size_gb < min_gb:
                    continue
                if max_gb is not None and model_size_gb > max_gb:
                    continue

            # Rule matched
            action = rule.get("action", {})
            target = action.get("target_compute", self._default_compute)
            provider = self._find_provider_by_compute(target)

            if provider:
                return RoutingDecision(
                    provider=provider,
                    model_id=action.get("model", ""),
                    tier=f"rule:{rule.get('id', 'unknown')}",
                    fallback_chain=self._build_rule_fallback(action),
                    confidence=0.7,
                )
        return None

    def _find_provider_by_compute(self, compute: str) -> ProviderEndpoint | None:
        """Find a provider endpoint that handles the given compute type."""
        # Direct match on provider.compute
        for p in self._providers.values():
            if p.compute == compute:
                return p

        # Check lemonade backends (vulkan, npu, cpu)
        lemonade = self._providers.get("lemonade")
        if lemonade:
            backends = self._config.get("providers", {}).get("lemonade", {}).get("backends", {})
            if compute in backends:
                return lemonade

        return None

    def _build_fallback_chain(self, tier_cfg: dict[str, Any]) -> list[ProviderEndpoint]:
        """Build a fallback chain from tier config."""
        chain: list[ProviderEndpoint] = []
        fallback = tier_cfg.get("fallback")
        if fallback:
            provider = self._find_provider_by_compute(fallback)
            if provider:
                chain.append(provider)
        return chain

    def _build_rule_fallback(self, action: dict[str, Any]) -> list[ProviderEndpoint]:
        """Build a fallback chain from a rule action."""
        chain: list[ProviderEndpoint] = []
        fallback = action.get("fallback")
        if fallback:
            provider = self._find_provider_by_compute(fallback)
            if provider:
                chain.append(provider)
        return chain
