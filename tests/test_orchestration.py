"""Tests for core/orchestration — models, ledger, registry, session,
router, watchdogs, workflow engine, discussion engine, bridge adapter,
memory bridge, and views."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ── Models ──────────────────────────────────────────────────────────────────


class TestWorkflowModel:
    """Tests for the Workflow Pydantic model."""

    def test_default_values(self):
        from core.orchestration.models import Workflow, WorkflowMode, WorkflowStatus

        wf = Workflow()
        assert wf.mode == WorkflowMode.COOPERATIVE
        assert wf.status == WorkflowStatus.CREATED
        assert wf.driver_agent_id is None
        assert wf.request == ""
        assert wf.final_synthesis is None
        assert wf.error is None
        assert isinstance(wf.workflow_id, str)
        assert len(wf.workflow_id) == 36  # UUID4

    def test_custom_values(self):
        from core.orchestration.models import Workflow, WorkflowMode, WorkflowStatus

        now = datetime.now(timezone.utc)
        wf = Workflow(
            workflow_id="test-123",
            mode=WorkflowMode.DISCUSSION,
            status=WorkflowStatus.RUNNING,
            driver_agent_id="research",
            request="Investigate X",
            request_class="task",
        )
        assert wf.workflow_id == "test-123"
        assert wf.mode == WorkflowMode.DISCUSSION
        assert wf.status == WorkflowStatus.RUNNING
        assert wf.driver_agent_id == "research"
        assert wf.request_class == "task"

    def test_updated_at_synced_to_created_at(self):
        from core.orchestration.models import Workflow

        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        wf = Workflow(created_at=past, updated_at=past - timedelta(hours=1))
        assert wf.updated_at == wf.created_at

    def test_status_enum_values(self):
        from core.orchestration.models import WorkflowStatus

        assert WorkflowStatus.CREATED == "created"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.SUSPENDED == "suspended"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.CANCELLED == "cancelled"

    def test_mode_enum_values(self):
        from core.orchestration.models import WorkflowMode

        assert WorkflowMode.COOPERATIVE == "cooperative"
        assert WorkflowMode.DISCUSSION == "discussion"


class TestWorkItemModel:
    def test_default_values(self):
        from core.orchestration.models import WorkItem, WorkItemStatus

        item = WorkItem()
        assert item.status == WorkItemStatus.PENDING
        assert item.priority == 5
        assert item.depends_on == []
        assert item.agent_id is None
        assert item.result is None

    def test_with_dependencies(self):
        from core.orchestration.models import WorkItem

        item = WorkItem(
            workflow_id="wf-1",
            depends_on=["item-1", "item-2"],
            priority=1,
            agent_id="research",
        )
        assert item.depends_on == ["item-1", "item-2"]
        assert item.priority == 1


class TestSwarmNoteModel:
    def test_default_values(self):
        from core.orchestration.models import SwarmNote

        note = SwarmNote()
        assert note.confidence == 1.0
        assert note.note_type == "observation"
        assert note.embedding is None

    def test_confidence_bounds(self):
        from core.orchestration.models import SwarmNote

        with pytest.raises(Exception):  # Pydantic ValidationError
            SwarmNote(confidence=1.5)
        with pytest.raises(Exception):
            SwarmNote(confidence=-0.1)


class TestClaimModel:
    def test_default_status(self):
        from core.orchestration.models import Claim

        claim = Claim()
        assert claim.status == "claimed"
        assert claim.confidence == 0.8


class TestReceiptModel:
    def test_default_outcome(self):
        from core.orchestration.models import Receipt

        receipt = Receipt()
        assert receipt.outcome == "success"
        assert receipt.target_type == ""


class TestInterruptModel:
    def test_interrupt_kinds(self):
        from core.orchestration.models import InterruptKind

        expected_values = [
            "user_input", "approval", "timeout", "error",
            "storm_detected", "novelty_low", "velocity_high",
            "receipt_absent", "external",
        ]
        actual_values = [m.value for m in InterruptKind]
        for kind in expected_values:
            assert kind in actual_values


# ── Registry ────────────────────────────────────────────────────────────────


class TestAgentRegistry:
    def test_load_manifests_from_dir(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        manifest = {
            "agent_id": "test_agent",
            "name": "Test Agent",
            "model_tier": "cloud-primary",
            "capabilities": ["test-cap"],
            "description": "A test agent",
            "tools": [
                {
                    "name": "test_tool",
                    "description": "Does test things",
                    "parameters": {"input": {"type": "string"}},
                    "risk_level": "high",
                }
            ],
        }

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "test_agent.yaml").write_text(
            __import__("yaml").dump(manifest)
        )

        registry = AgentRegistry()
        count = registry.load_manifests(str(agents_dir))
        assert count == 1

        agent = registry.get("test_agent")
        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.model_tier == "cloud-primary"
        assert agent.capabilities == ["test-cap"]
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "test_tool"
        assert agent.tools[0].risk_level == "high"

    def test_load_nonexistent_dir(self):
        from core.orchestration.registry import AgentRegistry

        registry = AgentRegistry()
        count = registry.load_manifests("/nonexistent/path")
        assert count == 0

    def test_get_nonexistent_agent(self):
        from core.orchestration.registry import AgentRegistry

        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_find_by_capability(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        for name, caps in [
            ("a", ["web-research", "summarization"]),
            ("b", ["web-research"]),
            ("c", ["security"]),
        ]:
            agents_dir = tmp_path / "agents"
            agents_dir.mkdir(exist_ok=True)
            (agents_dir / f"{name}.yaml").write_text(
                __import__("yaml").dump({
                    "agent_id": name,
                    "name": name,
                    "capabilities": caps,
                })
            )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))

        results = registry.find_by_capability("web-research")
        assert len(results) == 2
        assert {a.agent_id for a in results} == {"a", "b"}

    def test_is_allowed_no_restrictions(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "open.yaml").write_text(
            __import__("yaml").dump({
                "agent_id": "open_agent",
                "name": "Open",
            })
        )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))
        assert registry.is_allowed("open_agent", source_agent_id="anyone") is True

    def test_is_allowed_with_allow_from(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "restricted.yaml").write_text(
            __import__("yaml").dump({
                "agent_id": "restricted",
                "name": "Restricted",
                "allowFrom": ["driver", "telegram"],
            })
        )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))
        assert registry.is_allowed("restricted", source_agent_id="driver") is True
        assert registry.is_allowed("restricted", source_agent_id="unknown") is False
        assert registry.is_allowed("restricted", source_channel="telegram") is True

    def test_is_allowed_nonexistent_agent(self):
        from core.orchestration.registry import AgentRegistry

        registry = AgentRegistry()
        assert registry.is_allowed("ghost") is False

    def test_summary(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "x.yaml").write_text(
            __import__("yaml").dump({
                "agent_id": "x",
                "name": "X Agent",
                "model_tier": "local-small",
                "capabilities": ["a", "b"],
                "tools": [{"name": "t1", "description": "d1"}],
            })
        )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))
        summary = registry.summary()
        assert "x" in summary
        assert summary["x"]["tool_count"] == 1

    def test_high_risk_tools(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "risky.yaml").write_text(
            __import__("yaml").dump({
                "agent_id": "risky",
                "name": "Risky",
                "tools": [
                    {"name": "safe", "description": "ok", "risk_level": "low"},
                    {"name": "danger", "description": "nope", "risk_level": "high"},
                    {"name": "nuke", "description": "boom", "risk_level": "critical"},
                ],
            })
        )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))
        agent = registry.get("risky")
        assert len(agent.high_risk_tools) == 2

    def test_conversation_group(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        for name, group in [("a", "research_team"), ("b", "research_team"), ("c", None)]:
            (agents_dir / f"{name}.yaml").write_text(
                __import__("yaml").dump({
                    "agent_id": name,
                    "name": name,
                    "conversation_group": group,
                })
            )

        registry = AgentRegistry()
        registry.load_manifests(str(agents_dir))
        team = registry.find_by_conversation_group("research_team")
        assert len(team) == 2

    def test_invalid_manifest_skipped(self, tmp_path):
        from core.orchestration.registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "noid.yaml").write_text("name: NoId\n")
        # Empty file → yaml.safe_load returns None → skipped
        (agents_dir / "empty.yaml").write_text("")
        (agents_dir / "noid.yaml").write_text("name: NoId\n")

        registry = AgentRegistry()
        count = registry.load_manifests(str(agents_dir))
        assert count == 0


# ── Session Classifier ─────────────────────────────────────────────────────


class TestSessionClassifier:
    def _make_classifier(self, ledger=None, **kwargs):
        from core.orchestration.session import SessionClassifier

        return SessionClassifier(ledger or MagicMock(), **kwargs)

    def test_classify_question(self):
        cls = self._make_classifier()
        assert cls.classify_request_text("What is the meaning of life?") == "question"
        assert cls.classify_request_text("How do I fix this?") == "question"
        assert cls.classify_request_text("Explain quantum physics") == "question"

    def test_classify_debug(self):
        cls = self._make_classifier()
        assert cls.classify_request_text("Fix the broken pipeline") == "debug"
        assert cls.classify_request_text("Debug this crash") == "debug"

    def test_classify_task(self):
        cls = self._make_classifier()
        assert cls.classify_request_text("Summarize the meeting notes") == "task"
        assert cls.classify_request_text("Create a new API endpoint") == "task"
        assert cls.classify_request_text("Research the best approach") == "task"

    def test_classify_default(self):
        cls = self._make_classifier()
        assert cls.classify_request_text("random stuff xyz") == "task"

    def test_add_custom_rule(self):
        cls = self._make_classifier()
        cls.add_class_rule("deploy", "deployment")
        assert cls.classify_request_text("Deploy to production") == "deployment"

    def test_custom_rule_takes_priority(self):
        cls = self._make_classifier()
        cls.add_class_rule("build", "deployment")
        assert cls.classify_request_text("Build the thing") == "deployment"

    @pytest.mark.asyncio
    async def test_classify_creates_workflow(self):
        ledger = MagicMock()
        ledger.create_workflow = AsyncMock()
        ledger.list_workflows = AsyncMock(return_value=[])

        cls = self._make_classifier(ledger)
        wf_id, is_new = await cls.classify("Fix the crash")

        assert is_new is True
        assert isinstance(wf_id, str)
        ledger.create_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_preflight_nonexistent(self):
        ledger = MagicMock()
        ledger.get_workflow = AsyncMock(return_value=None)
        cls = self._make_classifier(ledger)
        result = await cls.preflight_check("nonexistent")
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_preflight_stale(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        now = datetime.now(timezone.utc)
        past = now - timedelta(seconds=600)
        wf = Workflow(
            status=WorkflowStatus.RUNNING,
            created_at=past,
            updated_at=past,
        )
        ledger = MagicMock()
        ledger.get_workflow = AsyncMock(return_value=wf)
        cls = self._make_classifier(ledger, stale_threshold=300)
        result = await cls.preflight_check("wf-1")
        assert result["is_stale"] is True

    @pytest.mark.asyncio
    async def test_preflight_fresh(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        now = datetime.now(timezone.utc)
        wf = Workflow(
            status=WorkflowStatus.COMPLETED,
            completed_at=now - timedelta(seconds=100),
        )
        ledger = MagicMock()
        ledger.get_workflow = AsyncMock(return_value=wf)
        cls = self._make_classifier(ledger, freshness_window=3600)
        result = await cls.preflight_check("wf-1")
        assert result["is_fresh"] is True


# ── Compute Router ──────────────────────────────────────────────────────────


class TestComputeRouter:
    def _make_router(self, config=None):
        from core.orchestration.router import ComputeRouter

        if config is None:
            config = {
                "default_compute": "cpu",
                "providers": {
                    "ollama": {"base_url": "http://localhost:11434", "api_style": "ollama", "compute": "nvidia"},
                    "lemonade": {
                        "base_url": "http://localhost:13305",
                        "api_style": "openai",
                        "compute": "npu",
                        "backends": {
                            "vulkan": {"compute": "amd_vulkan"},
                            "npu": {"compute": "npu"},
                            "cpu": {"compute": "cpu"},
                        },
                    },
                    "cloud_zai": {"base_url": "https://api.z.ai", "api_style": "openai", "compute": "cloud"},
                },
                "backend_tiers": {
                    "swarm_local_fast": {
                        "target_compute": "npu",
                        "fallback": "cpu",
                        "models": ["qwen3-0.6b-FLM"],
                    },
                    "worker_local_medium": {
                        "target_compute": "npu",
                        "fallback": "amd_vulkan",
                        "models": ["qwen3-tk-4b-FLM"],
                    },
                    "gpu_local_large": {
                        "target_compute": "nvidia",
                        "fallback": "amd_vulkan",
                        "models": ["gemma4:latest"],
                    },
                },
                "rules": [],
                "npu_policy": {
                    "warm_priority": ["qwen3-tk-4b-FLM", "embed-gemma-300m-FLM"],
                },
            }
        return ComputeRouter(config)

    def test_providers_loaded(self):
        router = self._make_router()
        assert len(router.providers) == 3
        assert "ollama" in router.providers
        assert "lemonade" in router.providers

    def test_available_tiers(self):
        router = self._make_router()
        tiers = router.available_tiers
        assert "swarm_local_fast" in tiers
        assert "worker_local_medium" in tiers
        assert "gpu_local_large" in tiers

    @pytest.mark.asyncio
    async def test_resolve_by_tier(self):
        router = self._make_router()
        decision = await router.resolve(capability_tier="worker_local_medium")
        assert decision.model_id == "qwen3-tk-4b-FLM"
        assert decision.tier == "worker_local_medium"

    @pytest.mark.asyncio
    async def test_resolve_preferred_model(self):
        router = self._make_router()
        decision = await router.resolve(preferred_model="gemma4:latest")
        assert decision.model_id == "gemma4:latest"
        assert decision.tier == "gpu_local_large"

    @pytest.mark.asyncio
    async def test_resolve_rule_based(self):
        config = self._make_router()._config
        config["rules"] = [
            {
                "id": "test_rule",
                "trigger": {"task_type": "embedding"},
                "action": {"target_compute": "npu", "model": "embed-model"},
                "priority": 10,
            }
        ]
        router = self._make_router(config)
        decision = await router.resolve(task_type="embedding")
        assert "rule" in decision.tier
        assert decision.model_id == "embed-model"

    def test_npu_hot_model(self):
        router = self._make_router()
        assert router.get_npu_hot_model() == "qwen3-tk-4b-FLM"
        router.set_npu_hot_model("other-model")
        assert router.get_npu_hot_model() == "other-model"

    def test_get_endpoint(self):
        router = self._make_router()
        ep = router.get_endpoint("ollama")
        assert ep is not None
        assert ep.compute == "nvidia"
        assert router.get_endpoint("nonexistent") is None


# ── Watchdogs ───────────────────────────────────────────────────────────────


class TestTokenBudgetWatchdog:
    def test_healthy_usage(self):
        from core.orchestration.models import Receipt
        from core.orchestration.watchdogs import TokenBudgetWatchdog

        wd = TokenBudgetWatchdog(max_tokens_in=10000, max_tokens_out=5000)
        receipts = [
            Receipt(tokens_in=1000, tokens_out=500),
            Receipt(tokens_in=2000, tokens_out=1000),
        ]
        assert wd.check("wf-1", receipts) is None

    def test_over_budget(self):
        from core.orchestration.models import Receipt
        from core.orchestration.watchdogs import TokenBudgetWatchdog

        wd = TokenBudgetWatchdog(max_tokens_in=5000, max_tokens_out=5000)
        receipts = [Receipt(tokens_in=6000, tokens_out=3000)]
        intr = wd.check("wf-1", receipts)
        assert intr is not None
        assert intr.kind.value == "velocity_high"
        assert "exceeded" in intr.message.lower()

    def test_warning_threshold(self):
        from core.orchestration.models import Receipt
        from core.orchestration.watchdogs import TokenBudgetWatchdog

        wd = TokenBudgetWatchdog(max_tokens_in=10000, max_tokens_out=5000, warn_pct=0.8)
        receipts = [Receipt(tokens_in=8500, tokens_out=1000)]
        intr = wd.check("wf-1", receipts)
        assert intr is not None
        assert intr.context.get("is_warning") is True


class TestNoveltyWatchdog:
    def test_all_unique(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.watchdogs import NoveltyWatchdog

        wd = NoveltyWatchdog(min_notes_before_check=3)
        notes = [
            SwarmNote(content=f"Unique note number {i}")
            for i in range(10)
        ]
        assert wd.check("wf-1", notes) is None

    def test_all_duplicates(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.watchdogs import NoveltyWatchdog

        wd = NoveltyWatchdog(min_notes_before_check=3, min_novelty_ratio=0.5)
        notes = [SwarmNote(content="Same content over and over")] * 10
        intr = wd.check("wf-1", notes)
        assert intr is not None
        assert intr.kind.value == "novelty_low"

    def test_too_few_notes(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.watchdogs import NoveltyWatchdog

        wd = NoveltyWatchdog(min_notes_before_check=10)
        notes = [SwarmNote(content="x")] * 3
        assert wd.check("wf-1", notes) is None

    def test_near_duplicate_content(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.watchdogs import NoveltyWatchdog

        wd = NoveltyWatchdog(min_notes_before_check=2, min_novelty_ratio=0.8)
        notes = [
            SwarmNote(content="The system needs to be updated"),
            SwarmNote(content="the system needs to be updated"),  # same normalized
            SwarmNote(content="the system needs to be updated"),  # same normalized
            SwarmNote(content="Completely different thing"),
        ]
        intr = wd.check("wf-1", notes)
        assert intr is not None
        assert intr.context["unique_notes"] < len(notes)


class TestVelocityWatchdog:
    def test_healthy_velocity(self):
        from core.orchestration.models import Receipt, SwarmNote
        from core.orchestration.watchdogs import VelocityWatchdog

        wd = VelocityWatchdog(max_notes_per_minute=30, window_seconds=60)
        now = datetime.now(timezone.utc)
        notes = [
            SwarmNote(created_at=now - timedelta(seconds=i * 5))
            for i in range(5)
        ]
        assert wd.check("wf-1", notes, []) is None

    def test_note_storm(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.watchdogs import VelocityWatchdog

        wd = VelocityWatchdog(max_notes_per_minute=5, window_seconds=60)
        now = datetime.now(timezone.utc)
        notes = [
            SwarmNote(created_at=now - timedelta(seconds=i))
            for i in range(10)
        ]
        intr = wd.check("wf-1", notes, [])
        assert intr is not None
        assert intr.kind.value == "storm_detected"

    def test_receipt_storm(self):
        from core.orchestration.models import Receipt
        from core.orchestration.watchdogs import VelocityWatchdog

        wd = VelocityWatchdog(max_receipts_per_minute=3, window_seconds=60)
        now = datetime.now(timezone.utc)
        receipts = [
            Receipt(created_at=now - timedelta(seconds=i * 5))
            for i in range(10)
        ]
        intr = wd.check("wf-1", [], receipts)
        assert intr is not None
        assert "receipts" in intr.message.lower()


class TestReceiptWatchdog:
    def test_no_in_progress_items(self):
        from core.orchestration.models import WorkItem, WorkItemStatus
        from core.orchestration.watchdogs import ReceiptWatchdog

        wd = ReceiptWatchdog(timeout_seconds=60)
        items = [WorkItem(status=WorkItemStatus.COMPLETED)]
        assert wd.check_work_items("wf-1", items, []) == []

    def test_missing_receipt(self):
        from core.orchestration.models import WorkItem, WorkItemStatus
        from core.orchestration.watchdogs import ReceiptWatchdog

        wd = ReceiptWatchdog(timeout_seconds=10)
        now = datetime.now(timezone.utc)
        items = [
            WorkItem(
                item_id="item-1",
                status=WorkItemStatus.IN_PROGRESS,
                agent_id="worker",
                started_at=now - timedelta(seconds=30),
                description="Do something",
            )
        ]
        interrupts = wd.check_work_items("wf-1", items, [])
        assert len(interrupts) == 1
        assert interrupts[0].kind.value == "receipt_absent"

    def test_receipt_present(self):
        from core.orchestration.models import Receipt, WorkItem, WorkItemStatus
        from core.orchestration.watchdogs import ReceiptWatchdog

        wd = ReceiptWatchdog(timeout_seconds=10)
        now = datetime.now(timezone.utc)
        items = [
            WorkItem(
                item_id="item-1",
                status=WorkItemStatus.IN_PROGRESS,
                started_at=now - timedelta(seconds=30),
            )
        ]
        receipts = [Receipt(target_type="work_item", target_id="item-1")]
        assert wd.check_work_items("wf-1", items, receipts) == []

    def test_not_yet_timed_out(self):
        from core.orchestration.models import WorkItem, WorkItemStatus
        from core.orchestration.watchdogs import ReceiptWatchdog

        wd = ReceiptWatchdog(timeout_seconds=300)
        now = datetime.now(timezone.utc)
        items = [
            WorkItem(
                item_id="item-1",
                status=WorkItemStatus.IN_PROGRESS,
                started_at=now - timedelta(seconds=10),
            )
        ]
        assert wd.check_work_items("wf-1", items, []) == []


# ── Cooperative Engine ──────────────────────────────────────────────────────


class TestCooperativeEngine:
    def _make_engine(self, ledger=None):
        from core.orchestration.workflow import CooperativeEngine

        if ledger is None:
            ledger = MagicMock()
            ledger.create_work_item = AsyncMock()
            ledger.update_workflow_status = AsyncMock(return_value=True)
            ledger.update_work_item = AsyncMock(return_value=True)
            ledger.get_pending_work_items = AsyncMock(return_value=[])
            ledger.get_work_items = AsyncMock(return_value=[])
            ledger.add_receipt = AsyncMock()
            ledger.add_swarm_note = AsyncMock()
            ledger.add_decision = AsyncMock()
            ledger.add_interrupt = AsyncMock()
            ledger.get_swarm_notes = AsyncMock(return_value=[])
            ledger.get_receipts = AsyncMock(return_value=[])
            ledger.get_unresolved_interrupts = AsyncMock(return_value=[])

        return CooperativeEngine(ledger)

    @pytest.mark.asyncio
    async def test_start_workflow_creates_items(self):
        from core.orchestration.models import WorkItem, WorkflowStatus

        ledger = MagicMock()
        ledger.create_work_item = AsyncMock()
        ledger.update_workflow_status = AsyncMock(return_value=True)
        ledger.get_pending_work_items = AsyncMock(return_value=[])
        ledger.get_work_items = AsyncMock(return_value=[])
        ledger.add_receipt = AsyncMock()
        ledger.add_swarm_note = AsyncMock()
        ledger.add_decision = AsyncMock()
        ledger.add_interrupt = AsyncMock()
        ledger.get_swarm_notes = AsyncMock(return_value=[])
        ledger.get_receipts = AsyncMock(return_value=[])
        ledger.get_unresolved_interrupts = AsyncMock(return_value=[])

        engine = self._make_engine(ledger)
        items = [
            WorkItem(description="Task 1"),
            WorkItem(description="Task 2"),
        ]

        await engine.start_workflow("wf-1", items)
        assert ledger.create_work_item.call_count == 2
        ledger.update_workflow_status.assert_called_with("wf-1", WorkflowStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_submit_receipt_success(self):
        from core.orchestration.models import Receipt, WorkItemStatus

        engine = self._make_engine()
        receipt = Receipt(
            workflow_id="wf-1",
            agent_id="worker",
            target_type="work_item",
            target_id="item-1",
            outcome="success",
            result_summary="Done!",
        )
        await engine.submit_receipt(receipt)
        engine._ledger.add_receipt.assert_called_once_with(receipt)
        engine._ledger.update_work_item.assert_called_with(
            "item-1", status=WorkItemStatus.COMPLETED, result="Done!"
        )

    @pytest.mark.asyncio
    async def test_submit_receipt_failure(self):
        from core.orchestration.models import Receipt, WorkItemStatus

        engine = self._make_engine()
        receipt = Receipt(
            workflow_id="wf-1",
            agent_id="worker",
            target_type="work_item",
            target_id="item-1",
            outcome="failure",
            error_detail="Boom",
        )
        await engine.submit_receipt(receipt)
        engine._ledger.update_work_item.assert_called_with(
            "item-1", status=WorkItemStatus.FAILED, error="Boom"
        )

    @pytest.mark.asyncio
    async def test_submit_receipt_partial(self):
        from core.orchestration.models import Receipt

        engine = self._make_engine()
        receipt = Receipt(
            workflow_id="wf-1",
            agent_id="worker",
            target_type="work_item",
            target_id="item-1",
            outcome="partial",
            result_summary="Half done",
        )
        await engine.submit_receipt(receipt)
        engine._ledger.add_swarm_note.assert_called_once()
        note = engine._ledger.add_swarm_note.call_args[0][0]
        assert "Partial" in note.content

    @pytest.mark.asyncio
    async def test_cancel_workflow(self):
        from core.orchestration.models import WorkflowStatus

        engine = self._make_engine()
        result = await engine.cancel_workflow("wf-1")
        assert result is True
        engine._ledger.update_workflow_status.assert_called_with(
            "wf-1", WorkflowStatus.CANCELLED
        )

    @pytest.mark.asyncio
    async def test_add_work_items(self):
        from core.orchestration.models import WorkItem

        engine = self._make_engine()
        items = [WorkItem(description="New task")]
        await engine.add_work_items("wf-1", items)
        engine._ledger.create_work_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_note(self):
        from core.orchestration.models import SwarmNote

        engine = self._make_engine()
        note = SwarmNote(workflow_id="wf-1", agent_id="worker", content="Obs")
        await engine.submit_note(note)
        engine._ledger.add_swarm_note.assert_called_once_with(note)

    @pytest.mark.asyncio
    async def test_submit_decision(self):
        from core.orchestration.models import DecisionPacket

        engine = self._make_engine()
        dp = DecisionPacket(workflow_id="wf-1", agent_id="driver", decision_type="route")
        await engine.submit_decision(dp)
        engine._ledger.add_decision.assert_called_once_with(dp)


# ── Discussion Engine ───────────────────────────────────────────────────────


class TestDiscussionEngine:
    def _make_engine(self, ledger=None):
        from core.orchestration.discussion import DiscussionEngine

        if ledger is None:
            ledger = MagicMock()
            ledger.update_workflow_status = AsyncMock(return_value=True)
            ledger.create_claim = AsyncMock()
            ledger.update_claim_status = AsyncMock()
            ledger.add_swarm_note = AsyncMock()
            ledger.add_decision = AsyncMock()
            ledger.add_interrupt = AsyncMock()
            ledger.get_claims = AsyncMock(return_value=[])
            ledger.get_swarm_notes = AsyncMock(return_value=[])
            ledger.get_receipts = AsyncMock(return_value=[])
            ledger.get_unresolved_interrupts = AsyncMock(return_value=[])
            ledger.get_workflow = AsyncMock(return_value=None)

        return DiscussionEngine(ledger)

    @pytest.mark.asyncio
    async def test_submit_claim(self):
        from core.orchestration.models import Claim

        engine = self._make_engine()
        claim = Claim(workflow_id="wf-1", agent_id="a1", portion_description="Part A")
        await engine.submit_claim(claim)
        engine._ledger.create_claim.assert_called_once_with(claim)

    @pytest.mark.asyncio
    async def test_submit_attack(self):
        from core.orchestration.discussion import DiscussionEngine
        from core.orchestration.models import SwarmNote

        engine = self._make_engine()
        note = await engine.submit_attack(
            "wf-1", "critic", "claim-1", "This analysis is incomplete"
        )
        assert isinstance(note, SwarmNote)
        assert note.role == "critic"
        assert note.target_claim_id == "claim-1"
        engine._ledger.update_claim_status.assert_called_with("claim-1", "attacked")

    @pytest.mark.asyncio
    async def test_submit_synthesis(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        wf = Workflow(status=WorkflowStatus.RUNNING)
        ledger = MagicMock()
        ledger.update_workflow_status = AsyncMock(return_value=True)
        ledger.add_decision = AsyncMock()
        ledger.get_workflow = AsyncMock(return_value=wf)
        ledger.get_claims = AsyncMock(return_value=[])
        ledger.get_swarm_notes = AsyncMock(return_value=[])
        ledger.get_receipts = AsyncMock(return_value=[])
        ledger.get_unresolved_interrupts = AsyncMock(return_value=[])

        engine = self._make_engine(ledger)
        dp = await engine.submit_synthesis("wf-1", "driver", "Final answer")
        assert dp.decision_type == "synthesize"
        ledger.update_workflow_status.assert_called_with(
            "wf-1", WorkflowStatus.COMPLETED, final_synthesis="Final answer"
        )

    @pytest.mark.asyncio
    async def test_cancel_discussion(self):
        from core.orchestration.models import WorkflowStatus

        engine = self._make_engine()
        result = await engine.cancel_discussion("wf-1")
        assert result is True
        engine._ledger.update_workflow_status.assert_called_with(
            "wf-1", WorkflowStatus.CANCELLED
        )


# ── Bridge Adapter ──────────────────────────────────────────────────────────


class TestBridgeAdapter:
    def _make_adapter(self):
        from core.orchestration.bridge_adapter import BridgeAdapter

        classifier = MagicMock()
        classifier.classify = AsyncMock(return_value=("wf-1", True))

        cooperative = MagicMock()
        discussion = MagicMock()
        discussion.start_discussion = AsyncMock()

        return BridgeAdapter(classifier, cooperative, discussion), classifier

    @pytest.mark.asyncio
    async def test_task_request_creates_workflow(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(
            type="task_request",
            correlation_id="corr-1",
            payload={"text": "Fix the build"},
        )
        event = await adapter.handle_message(msg, source_channel="telegram")
        assert event is not None
        assert event.category == "workflow_created"
        assert event.payload["mode"] == "cooperative"

    @pytest.mark.asyncio
    async def test_conversation_starts_discussion(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(
            type="conversation",
            payload={"text": "What do you think?"},
        )
        event = await adapter.handle_message(msg)
        assert event is not None
        assert event.category == "discussion_started"
        assert event.payload["mode"] == "discussion"

    @pytest.mark.asyncio
    async def test_heartbeat_ignored(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(type="heartbeat", payload={})
        event = await adapter.handle_message(msg)
        assert event is None

    @pytest.mark.asyncio
    async def test_unknown_type_ignored(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(type="unknown_type", payload={})
        event = await adapter.handle_message(msg)
        assert event is None

    @pytest.mark.asyncio
    async def test_task_request_no_text(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(type="task_request", payload={})
        event = await adapter.handle_message(msg)
        assert event is None

    @pytest.mark.asyncio
    async def test_approval_response(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(
            type="approval_response",
            payload={"workflow_id": "wf-1", "approved": True},
        )
        event = await adapter.handle_message(msg)
        assert event is not None
        assert event.category == "approval_resolved"
        assert event.payload["approved"] is True

    @pytest.mark.asyncio
    async def test_approval_response_missing_workflow_id(self):
        adapter, cls = self._make_adapter()
        from core.bridge.protocol import BridgeInboundMessage

        msg = BridgeInboundMessage(type="approval_response", payload={})
        event = await adapter.handle_message(msg)
        assert event is None


# ── Memory Bridge ───────────────────────────────────────────────────────────


class TestMemoryBridge:
    def _make_bridge(self, store=None):
        from core.orchestration.memory_bridge import MemoryBridge

        ledger = MagicMock()
        ledger.get_workflow = AsyncMock()
        ledger.get_decisions = AsyncMock(return_value=[])
        ledger.get_swarm_notes = AsyncMock(return_value=[])
        ledger.get_work_items = AsyncMock(return_value=[])
        ledger.get_claims = AsyncMock(return_value=[])

        return MemoryBridge(ledger, store or MagicMock()), ledger

    @pytest.mark.asyncio
    async def test_nonexistent_workflow(self):
        bridge, ledger = self._make_bridge()
        ledger.get_workflow = AsyncMock(return_value=None)
        count = await bridge.persist_workflow("ghost")
        assert count == 0

    @pytest.mark.asyncio
    async def test_non_completed_workflow_skipped(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        bridge, ledger = self._make_bridge()
        ledger.get_workflow = AsyncMock(
            return_value=Workflow(status=WorkflowStatus.RUNNING)
        )
        count = await bridge.persist_workflow("wf-1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_completed_workflow_persists_synthesis(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        bridge, ledger = self._make_bridge()
        store = MagicMock()
        store.add = AsyncMock()
        bridge._store = store

        ledger.get_workflow = AsyncMock(
            return_value=Workflow(
                status=WorkflowStatus.COMPLETED,
                final_synthesis="All done!",
            )
        )
        count = await bridge.persist_workflow("wf-1")
        assert count >= 1
        store.add.assert_called()

    @pytest.mark.asyncio
    async def test_no_store_returns_zero(self):
        from core.orchestration.models import Workflow, WorkflowStatus

        bridge, ledger = self._make_bridge(store=None)
        ledger.get_workflow = AsyncMock(
            return_value=Workflow(status=WorkflowStatus.COMPLETED, final_synthesis="x")
        )
        count = await bridge.persist_workflow("wf-1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_high_confidence_notes_persisted(self):
        from core.orchestration.models import SwarmNote, Workflow, WorkflowStatus

        bridge, ledger = self._make_bridge()
        store = MagicMock()
        store.add = AsyncMock()
        bridge._store = store

        ledger.get_workflow = AsyncMock(
            return_value=Workflow(status=WorkflowStatus.COMPLETED)
        )
        ledger.get_swarm_notes = AsyncMock(
            return_value=[
                SwarmNote(agent_id="a1", content="Insight", confidence=0.9, note_type="reasoning"),
                SwarmNote(agent_id="a2", content="Low conf", confidence=0.3, note_type="reasoning"),
            ]
        )
        count = await bridge.persist_workflow("wf-1")
        assert count >= 1


# ── Views ───────────────────────────────────────────────────────────────────


class TestWorkflowView:
    def test_workflow_summary(self):
        from core.orchestration.models import Workflow, WorkflowMode, WorkflowStatus
        from core.orchestration.views import WorkflowView

        wf = Workflow(
            workflow_id="abc12345-6789-0abc-def0-123456789abc",
            mode=WorkflowMode.COOPERATIVE,
            status=WorkflowStatus.RUNNING,
            driver_agent_id="research",
            request="Test request",
        )
        md = WorkflowView.workflow_summary(wf)
        assert "abc12345" in md
        assert "Cooperative" in md
        assert "running" in md
        assert "research" in md
        assert "Test request" in md

    def test_workflow_summary_with_synthesis(self):
        from core.orchestration.models import Workflow, WorkflowStatus
        from core.orchestration.views import WorkflowView

        wf = Workflow(
            status=WorkflowStatus.COMPLETED,
            final_synthesis="The answer is 42.",
        )
        md = WorkflowView.workflow_summary(wf)
        assert "The answer is 42." in md

    def test_work_items_table(self):
        from core.orchestration.models import WorkItem, WorkItemStatus
        from core.orchestration.views import WorkflowView

        items = [
            WorkItem(item_id="i-1", status=WorkItemStatus.PENDING, agent_id="a1", description="Task 1"),
            WorkItem(item_id="i-2", status=WorkItemStatus.COMPLETED, agent_id="a2", description="Task 2"),
        ]
        md = WorkflowView.work_items_table(items)
        assert "i-1" in md
        assert "i-2" in md
        assert "2 pending" in md or "1 pending" in md

    def test_work_items_table_empty(self):
        from core.orchestration.views import WorkflowView

        md = WorkflowView.work_items_table([])
        assert "No work items" in md

    def test_work_item_detail(self):
        from core.orchestration.models import WorkItem, WorkItemStatus
        from core.orchestration.views import WorkflowView

        item = WorkItem(
            item_id="detail-1",
            status=WorkItemStatus.FAILED,
            agent_id="worker",
            description="Do thing",
            error="Something broke",
        )
        md = WorkflowView.work_item_detail(item)
        assert "Something broke" in md
        assert "Do thing" in md

    def test_claims_table(self):
        from core.orchestration.models import Claim
        from core.orchestration.views import WorkflowView

        claims = [
            Claim(claim_id="c-1", agent_id="a1", portion_description="Part A", status="accepted"),
            Claim(claim_id="c-2", agent_id="a2", portion_description="Part B", status="rejected"),
        ]
        md = WorkflowView.claims_table(claims)
        assert "c-1" in md
        assert "c-2" in md

    def test_receipts_summary(self):
        from core.orchestration.models import Receipt
        from core.orchestration.views import WorkflowView

        receipts = [
            Receipt(
                target_type="work_item",
                target_id="item-1",
                agent_id="worker",
                model_used="gemma4",
                duration_ms=1500,
                tokens_in=500,
                tokens_out=200,
                result_summary="All good",
            ),
        ]
        md = WorkflowView.receipts_summary(receipts)
        assert "item-1" in md
        assert "500" in md  # input tokens
        assert "200" in md  # output tokens

    def test_receipts_summary_empty(self):
        from core.orchestration.views import WorkflowView

        md = WorkflowView.receipts_summary([])
        assert "No receipts" in md

    def test_swarm_notes_timeline(self):
        from core.orchestration.models import SwarmNote
        from core.orchestration.views import WorkflowView

        notes = [
            SwarmNote(agent_id="a1", role="driver", content="Starting"),
            SwarmNote(agent_id="a2", role="worker", content="Working"),
        ]
        md = WorkflowView.swarm_notes_timeline(notes)
        assert "a1" in md
        assert "driver" in md
        assert "Starting" in md

    def test_decisions_timeline(self):
        from core.orchestration.models import DecisionPacket
        from core.orchestration.views import WorkflowView

        decisions = [
            DecisionPacket(
                agent_id="driver",
                decision_type="route",
                trigger="task_complexity",
                chosen="cooperative",
                reasoning="Task has clear sub-steps",
                alternatives=[{"option": "discussion"}],
            )
        ]
        md = WorkflowView.decisions_timeline(decisions)
        assert "route" in md
        assert "cooperative" in md

    def test_interrupts_table(self):
        from core.orchestration.models import Interrupt, InterruptKind
        from core.orchestration.views import WorkflowView

        interrupts = [
            Interrupt(kind=InterruptKind.STORM_DETECTED, message="Too many notes"),
            Interrupt(kind=InterruptKind.NOVELTY_LOW, message="Redundant", resolution="resumed"),
        ]
        md = WorkflowView.interrupts_table(interrupts)
        assert "storm_detected" in md
        assert "resumed" in md

    def test_full_workflow_view(self):
        from core.orchestration.models import (
            Claim, DecisionPacket, Interrupt, InterruptKind,
            Receipt, SwarmNote, WorkItem, WorkItemStatus,
            Workflow, WorkflowMode, WorkflowStatus,
        )
        from core.orchestration.views import WorkflowView

        wf = Workflow(
            workflow_id="full-test-id",
            mode=WorkflowMode.COOPERATIVE,
            status=WorkflowStatus.COMPLETED,
            request="Full test",
            final_synthesis="Done!",
        )
        items = [WorkItem(item_id="i-1", status=WorkItemStatus.COMPLETED)]
        notes = [SwarmNote(agent_id="a1", content="Note")]
        claims = [Claim(claim_id="c-1", agent_id="a1")]
        receipts = [Receipt(target_type="work_item", target_id="i-1")]
        decisions = [DecisionPacket(agent_id="driver", decision_type="synthesize")]
        interrupts = [Interrupt(kind=InterruptKind.TIMEOUT, message="Slow")]

        md = WorkflowView.full_workflow_view(
            wf, items, notes, claims, receipts, decisions, interrupts
        )
        assert "Full test" in md
        assert "Done!" in md
        assert "Work Items" in md
        assert "Claims" in md
        assert "Interrupts" in md


# ── Gateway Integration ─────────────────────────────────────────────────────


class TestGatewayIntegration:
    @pytest.mark.asyncio
    async def test_init_orchestration_idempotent(self):
        from core.orchestration.gateway import init_orchestration

        app = SimpleNamespace(
            state=SimpleNamespace(
                orchestration_initialised=False,
                agents_dir="agents",
                pg_pool=None,
            ),
        )
        # Run twice — second should be no-op
        await init_orchestration(app)
        await init_orchestration(app)
        assert app.state.orchestration_initialised is True

    @pytest.mark.asyncio
    async def test_init_orchestration_without_pool(self):
        from core.orchestration.gateway import init_orchestration

        app = SimpleNamespace(
            state=SimpleNamespace(
                orchestration_initialised=False,
                agents_dir="agents",
                pg_pool=None,
            ),
        )
        await init_orchestration(app)
        assert app.state.orchestration_initialised is True
        # Ledger should not be set
        assert not hasattr(app.state, "orchestration_ledger") or app.state.orchestration_ledger is None

    def test_orchestration_health(self):
        from core.orchestration.gateway import orchestration_health

        app = SimpleNamespace(
            state=SimpleNamespace(
                agent_registry=None,
                compute_router=None,
                orchestration_ledger=None,
                cooperative_engine=None,
                discussion_engine=None,
            ),
        )
        health = orchestration_health(app)
        assert "registry" in health
        assert "compute_router" in health
        assert "ledger" in health

    def test_orchestration_health_with_components(self):
        from core.orchestration.gateway import orchestration_health

        registry = MagicMock()
        registry.agent_ids = ["a", "b"]
        router = MagicMock()
        router.available_tiers = ["fast", "medium"]

        app = SimpleNamespace(
            state=SimpleNamespace(
                agent_registry=registry,
                compute_router=router,
                orchestration_ledger=MagicMock(),
                cooperative_engine=MagicMock(_active_workflows={}),
                discussion_engine=MagicMock(_active={}),
            ),
        )
        health = orchestration_health(app)
        assert health["registry"]["agent_count"] == 2
        assert health["registry"]["status"] == "ok"


# ── Ledger (unit tests with mocked pool) ────────────────────────────────────


class TestLedger:
    def _make_ledger(self):
        from core.orchestration.ledger import Ledger

        pool = MagicMock()
        return Ledger(pool), pool

    @pytest.mark.asyncio
    async def test_create_workflow(self):
        from core.orchestration.models import Workflow

        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.execute = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        wf = Workflow(workflow_id="wf-1", request="Test")
        result = await ledger.create_workflow(wf)
        assert result.workflow_id == "wf-1"
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_none(self):
        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.fetchrow = AsyncMock(return_value=None)
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ledger.get_workflow("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_workflow_found(self):
        from core.orchestration.ledger import Ledger
        from core.orchestration.models import Workflow

        ledger, pool = self._make_ledger()
        row = {
            "workflow_id": "wf-1",
            "mode": "cooperative",
            "status": "running",
            "driver_agent_id": "driver",
            "request": "Test",
            "request_class": "task",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": None,
            "context": {},
            "metadata": {},
            "source_event_id": None,
            "source_channel": None,
            "correlation_id": None,
            "final_synthesis": None,
            "error": None,
        }
        conn = MagicMock()
        conn.fetchrow = AsyncMock(return_value=row)
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        wf = await ledger.get_workflow("wf-1")
        assert wf is not None
        assert wf.workflow_id == "wf-1"

    @pytest.mark.asyncio
    async def test_update_workflow_status_invalid_transition(self):
        from core.orchestration.models import WorkflowStatus
        from core.orchestration.ledger import Ledger

        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.fetchrow = AsyncMock(return_value={"status": "completed"})
        conn.execute = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ledger.update_workflow_status("wf-1", WorkflowStatus.RUNNING)
        assert result is False
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_receipt(self):
        from core.orchestration.models import Receipt

        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.execute = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        receipt = Receipt(
            workflow_id="wf-1",
            agent_id="worker",
            target_type="work_item",
            target_id="item-1",
        )
        result = await ledger.add_receipt(receipt)
        assert result.receipt_id == receipt.receipt_id

    @pytest.mark.asyncio
    async def test_get_pending_work_items(self):
        from core.orchestration.ledger import Ledger

        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.fetch = AsyncMock(return_value=[])
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        items = await ledger.get_pending_work_items("wf-1")
        assert items == []

    @pytest.mark.asyncio
    async def test_resolve_interrupt(self):
        ledger, pool = self._make_ledger()
        conn = MagicMock()
        # execute returns "UPDATE 1"
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ledger.resolve_interrupt("intr-1", "resumed")
        assert result is True

    @pytest.mark.asyncio
    async def test_resolve_interrupt_no_match(self):
        ledger, pool = self._make_ledger()
        conn = MagicMock()
        conn.execute = AsyncMock(return_value="UPDATE 0")
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ledger.resolve_interrupt("intr-1", "resumed")
        assert result is False
