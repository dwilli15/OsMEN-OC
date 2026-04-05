"""Tests for core/pipelines/runner.py.

Covers:
- Pipeline loading from config.
- Cron match logic.
- Step execution through approval + audit + event + handler.
- Pipeline execution dispatches all steps.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.approval.gate import ApprovalGate
from core.gateway.mcp import MCPTool
from core.pipelines.runner import Pipeline, PipelineRunner, PipelineStep

FIXTURES_DIR = Path(__file__).parent.parent / "config"


def _make_registry() -> dict[str, MCPTool]:
    tools = [
        MCPTool(agent_id="daily_brief", name="fetch_task_summary", risk_level="low"),
        MCPTool(agent_id="daily_brief", name="generate_brief", risk_level="low"),
        MCPTool(agent_id="knowledge_librarian", name="ingest_url", risk_level="low"),
        MCPTool(agent_id="media_organization", name="audit_vpn", risk_level="medium"),
        MCPTool(agent_id="media_organization", name="transfer_to_plex", risk_level="medium"),
        MCPTool(agent_id="media_organization", name="purge_completed", risk_level="medium"),
    ]
    return {t.name: t for t in tools}


def _mock_bus() -> AsyncMock:
    bus = AsyncMock()
    bus.publish = AsyncMock(return_value="1-0")
    return bus


class TestPipelineLoading:
    """Tests for pipeline config loading."""

    def test_load_pipelines_from_config(self) -> None:
        runner = PipelineRunner(
            event_bus=_mock_bus(),
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )
        pipelines = runner._load_pipelines()
        assert len(pipelines) == 4

        ids = {p.id for p in pipelines}
        assert ids == {"morning_brief", "evening_brief", "knowledge_ingest", "media_transfer"}

    def test_cron_pipelines_have_schedule(self) -> None:
        runner = PipelineRunner(
            event_bus=_mock_bus(),
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )
        pipelines = runner._load_pipelines()
        cron = [p for p in pipelines if p.trigger_type == "cron"]
        assert len(cron) == 2
        assert all(p.trigger_value for p in cron)

    def test_event_pipelines_have_stream(self) -> None:
        runner = PipelineRunner(
            event_bus=_mock_bus(),
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )
        pipelines = runner._load_pipelines()
        event_pipes = [p for p in pipelines if p.trigger_type == "event"]
        assert len(event_pipes) == 2
        streams = {p.trigger_value for p in event_pipes}
        assert "events:knowledge:ingest_requested" in streams
        assert "events:media:download_complete" in streams

    def test_pipeline_steps_parsed(self) -> None:
        runner = PipelineRunner(
            event_bus=_mock_bus(),
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )
        pipelines = runner._load_pipelines()
        morning = next(p for p in pipelines if p.id == "morning_brief")
        assert len(morning.steps) == 2
        assert morning.steps[0].tool == "fetch_task_summary"
        assert morning.steps[1].tool == "generate_brief"
        assert morning.steps[1].parameters == {"period": "morning"}


class TestCronMatch:
    """Tests for cron matching logic."""

    def test_exact_match(self) -> None:
        from datetime import UTC, datetime

        fake_now = datetime(2026, 4, 4, 7, 0, tzinfo=UTC)
        assert PipelineRunner._cron_matches_now("0 7 * * *", _now=fake_now) is True

    def test_no_match(self) -> None:
        from datetime import UTC, datetime

        fake_now = datetime(2026, 4, 4, 8, 30, tzinfo=UTC)
        assert PipelineRunner._cron_matches_now("0 7 * * *", _now=fake_now) is False

    def test_step_every_15_minutes(self) -> None:
        from datetime import UTC, datetime

        match_now = datetime(2026, 4, 4, 15, 30, tzinfo=UTC)
        miss_now = datetime(2026, 4, 4, 15, 31, tzinfo=UTC)
        assert PipelineRunner._cron_matches_now("*/15 * * * *", _now=match_now) is True
        assert PipelineRunner._cron_matches_now("*/15 * * * *", _now=miss_now) is False

    def test_weekday_constraint(self) -> None:
        from datetime import UTC, datetime

        # 2026-04-04 is Saturday.
        fake_now = datetime(2026, 4, 4, 7, 0, tzinfo=UTC)
        assert PipelineRunner._cron_matches_now("0 7 * * 6", _now=fake_now) is True
        assert PipelineRunner._cron_matches_now("0 7 * * 1", _now=fake_now) is False

    def test_invalid_cron_returns_false(self) -> None:
        assert PipelineRunner._cron_matches_now("") is False
        assert PipelineRunner._cron_matches_now("x") is False
        assert PipelineRunner._cron_matches_now("* * *") is False
        assert PipelineRunner._cron_matches_now("61 * * * *") is False


class TestStepExecution:
    """Tests for pipeline step execution through the approval→audit→event chain."""

    @pytest.mark.anyio
    async def test_execute_pipeline_publishes_events(self) -> None:
        bus = _mock_bus()
        runner = PipelineRunner(
            event_bus=bus,
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )

        pipeline = Pipeline(
            id="test_pipe",
            trigger_type="event",
            trigger_value="events:test:trigger",
            steps=[
                PipelineStep(agent="daily_brief", tool="fetch_task_summary"),
                PipelineStep(
                    agent="daily_brief",
                    tool="generate_brief",
                    parameters={"period": "test"},
                ),
            ],
        )

        await runner._execute_pipeline(pipeline, trigger_payload={"source": "test"})

        # 2 step events + 1 completion event = 3 publishes
        assert bus.publish.call_count == 3

        # Last call should be the completion event
        completion = bus.publish.call_args_list[-1][0][0]
        assert completion.domain == "pipelines"
        assert completion.category == "completed"
        assert completion.payload["pipeline_id"] == "test_pipe"

    @pytest.mark.anyio
    async def test_execute_step_writes_audit_when_pool_present(self) -> None:
        bus = _mock_bus()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _acquire():
            yield conn

        pool = MagicMock()
        pool.acquire = _acquire

        runner = PipelineRunner(
            event_bus=bus,
            mcp_registry=_make_registry(),
            approval_gate=ApprovalGate(),
            audit_trail_pool=pool,
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )

        step = PipelineStep(agent="daily_brief", tool="fetch_task_summary")
        tool = _make_registry()["fetch_task_summary"]

        await runner._execute_step("test_pipe", step, tool, {"key": "val"})

        # audit trail insert was called
        conn.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_missing_tool_skipped(self) -> None:
        bus = _mock_bus()
        runner = PipelineRunner(
            event_bus=bus,
            mcp_registry={},  # empty registry
            approval_gate=ApprovalGate(),
            config_path=FIXTURES_DIR / "pipelines.yaml",
        )

        pipeline = Pipeline(
            id="test_pipe",
            trigger_type="event",
            trigger_value="events:test:trigger",
            steps=[PipelineStep(agent="nobody", tool="nonexistent")],
        )

        await runner._execute_pipeline(pipeline, trigger_payload={})

        # Only the completion event should be published (step was skipped)
        assert bus.publish.call_count == 1
        completion = bus.publish.call_args_list[0][0][0]
        assert completion.category == "completed"
