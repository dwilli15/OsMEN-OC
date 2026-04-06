"""Tests for system_monitor builtin handlers.

Covers all 7 tools:
- get_hardware_metrics
- set_power_profile
- set_fan_curve
- get_compute_routing
- set_compute_routing
- intake_compute_routing
- get_npu_status
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from core.gateway.handlers import HandlerContext


def _make_completed(returncode: int, stdout: bytes, stderr: bytes = b""):
    """Build a subprocess.CompletedProcess for mocking anyio.run_process."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


_CTX = HandlerContext(agent_id="system_monitor")

# ---------------------------------------------------------------------------
# get_hardware_metrics
# ---------------------------------------------------------------------------


class TestGetHardwareMetrics:
    """Tests for the get_hardware_metrics handler."""

    @pytest.mark.anyio
    async def test_all_tools_unavailable(self) -> None:
        """When all CLI tools are missing, returns ok with errors list."""
        from core.gateway.builtin_handlers import handle_get_hardware_metrics

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            result = await handle_get_hardware_metrics({}, _CTX)

        assert result["status"] == "ok"
        assert len(result["errors"]) == 3
        assert any("lm-sensors" in e for e in result["errors"])
        assert any("nvidia-smi" in e for e in result["errors"])
        assert any("rocm-smi" in e for e in result["errors"])

    @pytest.mark.anyio
    async def test_sensors_json_returned(self) -> None:
        """Valid sensors JSON is parsed and returned under 'cpu' key."""
        from core.gateway.builtin_handlers import handle_get_hardware_metrics

        fake_sensors = {"coretemp-isa-0000": {"Core 0": {"temp1_input": 55.0}}}

        async def _fake_run_process(cmd, **kwargs):
            if cmd[0] == "sensors":
                return _make_completed(0, json.dumps(fake_sensors).encode())
            raise FileNotFoundError

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_get_hardware_metrics({}, _CTX)

        assert result["status"] == "ok"
        assert result["cpu"] == fake_sensors

    @pytest.mark.anyio
    async def test_nvidia_smi_parsed(self) -> None:
        """nvidia-smi CSV output is parsed into a list of GPU dicts."""
        from core.gateway.builtin_handlers import handle_get_hardware_metrics

        nvidia_csv = b"NVIDIA GeForce RTX 5070, 65, 70, 45, 85.5, 120, 1800, 9501, 3072, 8192\n"

        async def _fake_run_process(cmd, **kwargs):
            if cmd[0] == "sensors":
                raise FileNotFoundError
            if cmd[0] == "nvidia-smi":
                return _make_completed(0, nvidia_csv)
            raise FileNotFoundError

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_get_hardware_metrics({}, _CTX)

        assert result["status"] == "ok"
        assert "nvidia" in result
        assert isinstance(result["nvidia"], list)
        assert len(result["nvidia"]) == 1

    @pytest.mark.anyio
    async def test_sensors_nonzero_returncode(self) -> None:
        """Non-zero returncode from sensors adds an entry to errors."""
        from core.gateway.builtin_handlers import handle_get_hardware_metrics

        async def _fake_run_process(cmd, **kwargs):
            if cmd[0] == "sensors":
                return _make_completed(1, b"", b"sensors: no sensors found")
            raise FileNotFoundError

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_get_hardware_metrics({}, _CTX)

        assert result["status"] == "ok"
        assert any("sensors exited 1" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# set_power_profile
# ---------------------------------------------------------------------------


class TestSetPowerProfile:
    """Tests for the set_power_profile handler."""

    @pytest.mark.anyio
    async def test_unknown_profile(self) -> None:
        """Unknown named profile returns an error."""
        from core.gateway.builtin_handlers import handle_set_power_profile

        result = await handle_set_power_profile({"profile": "turbo"}, _CTX)
        assert result["status"] == "error"
        assert "turbo" in result["detail"]

    @pytest.mark.anyio
    async def test_no_parameters(self) -> None:
        """No parameters returns an error."""
        from core.gateway.builtin_handlers import handle_set_power_profile

        result = await handle_set_power_profile({}, _CTX)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_balanced_profile_calls_ryzenadj_and_nvidia(self) -> None:
        """balanced profile invokes ryzenadj and nvidia-smi."""
        from core.gateway.builtin_handlers import handle_set_power_profile

        calls: list[list[str]] = []

        async def _fake_run_process(cmd, **kwargs):
            calls.append(list(cmd))
            return _make_completed(0, b"OK")

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_set_power_profile({"profile": "balanced"}, _CTX)

        assert result["status"] == "ok"
        assert any(c[0] == "ryzenadj" for c in calls)
        assert any(c[0] == "nvidia-smi" for c in calls)

    @pytest.mark.anyio
    async def test_ryzenadj_not_installed(self) -> None:
        """Missing ryzenadj adds a useful install hint to errors."""
        from core.gateway.builtin_handlers import handle_set_power_profile

        async def _fake(cmd, **kwargs):
            if cmd[0] == "ryzenadj":
                raise FileNotFoundError
            return _make_completed(0, b"OK")

        with patch("core.gateway.builtin_handlers._anyio.run_process", side_effect=_fake):
            result = await handle_set_power_profile({"profile": "performance"}, _CTX)

        assert any("ryzenadj" in e for e in result["errors"])
        # nvidia-smi still applied
        assert any("nvidia-smi" in a for a in result["applied"])

    @pytest.mark.anyio
    async def test_explicit_watt_values(self) -> None:
        """Explicit watt parameters override profile defaults."""
        from core.gateway.builtin_handlers import handle_set_power_profile

        cmd_args: list[list[str]] = []

        async def _fake(cmd, **kwargs):
            cmd_args.append(list(cmd))
            return _make_completed(0, b"OK")

        with patch("core.gateway.builtin_handlers._anyio.run_process", side_effect=_fake):
            result = await handle_set_power_profile(
                {"amd_stapm_watts": 30, "nvidia_power_limit_watts": 70}, _CTX
            )

        assert result["status"] == "ok"
        rj_call = next(c for c in cmd_args if c[0] == "ryzenadj")
        assert any("30000" in arg for arg in rj_call)  # 30 W → 30000 mW
        nv_call = next(c for c in cmd_args if c[0] == "nvidia-smi")
        assert "70" in nv_call


# ---------------------------------------------------------------------------
# set_fan_curve
# ---------------------------------------------------------------------------


class TestSetFanCurve:
    """Tests for the set_fan_curve handler."""

    @pytest.mark.anyio
    async def test_missing_speed(self) -> None:
        """Missing speed_percent returns an error."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        result = await handle_set_fan_curve({}, _CTX)
        assert result["status"] == "error"
        assert "speed_percent" in result["detail"]

    @pytest.mark.anyio
    async def test_invalid_speed_string(self) -> None:
        """Non-numeric, non-auto speed_percent returns an error."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        result = await handle_set_fan_curve({"speed_percent": "fast"}, _CTX)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_out_of_range_speed(self) -> None:
        """speed_percent > 100 returns an error."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        result = await handle_set_fan_curve({"speed_percent": "150"}, _CTX)
        assert result["status"] == "error"
        assert "0" in result["detail"] and "100" in result["detail"]

    @pytest.mark.anyio
    async def test_auto_mode(self) -> None:
        """speed_percent='auto' calls nbfc set --auto."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        nbfc_cmd: list[str] = []

        async def _fake(cmd, **kwargs):
            nbfc_cmd.extend(cmd)
            return _make_completed(0, b"")

        with patch("core.gateway.builtin_handlers._anyio.run_process", side_effect=_fake):
            result = await handle_set_fan_curve({"speed_percent": "auto"}, _CTX)

        assert result["status"] == "ok"
        assert "--auto" in nbfc_cmd

    @pytest.mark.anyio
    async def test_numeric_speed_calls_nbfc(self) -> None:
        """Numeric speed calls nbfc set --speed <N>."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        nbfc_cmd: list[str] = []

        async def _fake(cmd, **kwargs):
            nbfc_cmd.extend(cmd)
            return _make_completed(0, b"")

        with patch("core.gateway.builtin_handlers._anyio.run_process", side_effect=_fake):
            result = await handle_set_fan_curve({"speed_percent": "75"}, _CTX)

        assert result["status"] == "ok"
        assert "--speed" in nbfc_cmd and "75" in nbfc_cmd

    @pytest.mark.anyio
    async def test_nbfc_not_installed(self) -> None:
        """Missing nbfc returns a helpful install message."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            result = await handle_set_fan_curve({"speed_percent": "50"}, _CTX)

        assert result["status"] == "error"
        assert "nbfc" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_fan_index_passed_to_nbfc(self) -> None:
        """fan_index is forwarded to nbfc as --fan <index>."""
        from core.gateway.builtin_handlers import handle_set_fan_curve

        nbfc_cmd: list[str] = []

        async def _fake(cmd, **kwargs):
            nbfc_cmd.extend(cmd)
            return _make_completed(0, b"")

        with patch("core.gateway.builtin_handlers._anyio.run_process", side_effect=_fake):
            result = await handle_set_fan_curve({"speed_percent": "60", "fan_index": 1}, _CTX)

        assert result["status"] == "ok"
        assert "--fan" in nbfc_cmd and "1" in nbfc_cmd


# ---------------------------------------------------------------------------
# get_compute_routing
# ---------------------------------------------------------------------------


class TestGetComputeRouting:
    """Tests for the get_compute_routing handler."""

    @pytest.mark.anyio
    async def test_reads_rules_from_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reads and returns rules from the config file."""
        from core.gateway.builtin_handlers import handle_get_compute_routing

        routing_file = tmp_path / "compute-routing.yaml"
        routing_file.write_text(
            "version: 1\ndefault_compute: cpu\nrules:\n  - id: test_rule\n    priority: 5\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(routing_file))

        result = await handle_get_compute_routing({}, _CTX)

        assert result["status"] == "ok"
        assert result["rule_count"] == 1
        assert result["default_compute"] == "cpu"

    @pytest.mark.anyio
    async def test_missing_file_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing config file returns ok with empty rules list."""
        from core.gateway.builtin_handlers import handle_get_compute_routing

        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(tmp_path / "nonexistent.yaml"))

        result = await handle_get_compute_routing({}, _CTX)

        assert result["status"] == "ok"
        assert result["rule_count"] == 0
        assert result["rules"] == []


# ---------------------------------------------------------------------------
# set_compute_routing
# ---------------------------------------------------------------------------


class TestSetComputeRouting:
    """Tests for the set_compute_routing handler."""

    @pytest.mark.anyio
    async def test_missing_rule_id(self) -> None:
        """Missing rule_id returns an error."""
        from core.gateway.builtin_handlers import handle_set_compute_routing

        result = await handle_set_compute_routing(
            {"target_compute": "nvidia", "description": "test"}, _CTX
        )
        assert result["status"] == "error"
        assert "rule_id" in result["detail"]

    @pytest.mark.anyio
    async def test_invalid_target_compute(self) -> None:
        """Invalid target_compute returns an error."""
        from core.gateway.builtin_handlers import handle_set_compute_routing

        result = await handle_set_compute_routing(
            {"rule_id": "test", "target_compute": "tpu", "description": "test"}, _CTX
        )
        assert result["status"] == "error"
        assert "target_compute" in result["detail"]

    @pytest.mark.anyio
    async def test_creates_new_rule(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Creates a new rule when rule_id does not exist."""
        from core.gateway.builtin_handlers import handle_set_compute_routing

        routing_file = tmp_path / "compute-routing.yaml"
        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(routing_file))

        result = await handle_set_compute_routing(
            {
                "rule_id": "my_rule",
                "description": "Route inference to NPU",
                "target_compute": "npu",
                "trigger_task_type": "inference",
                "priority": 10,
            },
            _CTX,
        )

        assert result["status"] == "ok"
        assert result["action"] == "created"
        assert routing_file.exists()

        saved = yaml.safe_load(routing_file.read_text())
        assert any(r["id"] == "my_rule" for r in saved["rules"])

    @pytest.mark.anyio
    async def test_updates_existing_rule(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Upserts an existing rule by rule_id."""
        from core.gateway.builtin_handlers import handle_set_compute_routing

        routing_file = tmp_path / "compute-routing.yaml"
        routing_file.write_text(
            "version: 1\ndefault_compute: cpu\nrules:\n"
            "  - id: my_rule\n    description: old\n    trigger: {}\n"
            "    action: {target_compute: cpu}\n    priority: 5\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(routing_file))

        result = await handle_set_compute_routing(
            {
                "rule_id": "my_rule",
                "description": "Updated rule",
                "target_compute": "nvidia",
                "priority": 20,
            },
            _CTX,
        )

        assert result["status"] == "ok"
        assert result["action"] == "updated"
        saved = yaml.safe_load(routing_file.read_text())
        rule = next(r for r in saved["rules"] if r["id"] == "my_rule")
        assert rule["action"]["target_compute"] == "nvidia"


# ---------------------------------------------------------------------------
# intake_compute_routing
# ---------------------------------------------------------------------------


class TestIntakeComputeRouting:
    """Tests for the intake_compute_routing handler."""

    @pytest.mark.anyio
    async def test_start_returns_first_question(self) -> None:
        """start=true initialises a session and returns Q1."""
        from core.gateway.builtin_handlers import handle_intake_compute_routing

        result = await handle_intake_compute_routing({"start": True}, _CTX)

        assert result["status"] == "ok"
        assert "session_id" in result
        assert result["question_index"] == 1
        assert result["total_questions"] == 20
        assert "question" in result

    @pytest.mark.anyio
    async def test_continue_session_advances(self) -> None:
        """Answering Q1 advances to Q2."""
        from core.gateway.builtin_handlers import handle_intake_compute_routing

        start = await handle_intake_compute_routing({"start": True}, _CTX)
        session_id = start["session_id"]

        r2 = await handle_intake_compute_routing(
            {"session_id": session_id, "answer": "yes"}, _CTX
        )
        assert r2["status"] == "ok"
        assert r2["question_index"] == 2

    @pytest.mark.anyio
    async def test_invalid_yn_answer_rejected(self) -> None:
        """Non-yes/no answer to a yn question is rejected."""
        from core.gateway.builtin_handlers import handle_intake_compute_routing

        start = await handle_intake_compute_routing({"start": True}, _CTX)
        session_id = start["session_id"]

        result = await handle_intake_compute_routing(
            {"session_id": session_id, "answer": "maybe"}, _CTX
        )
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_missing_session_id(self) -> None:
        """Missing session_id without start=true returns error."""
        from core.gateway.builtin_handlers import handle_intake_compute_routing

        result = await handle_intake_compute_routing({"answer": "yes"}, _CTX)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_full_interview_no_commit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Full 20-question run with commit=no does not write the config."""
        from core.gateway.builtin_handlers import (
            _INTAKE_QUESTIONS,
            handle_intake_compute_routing,
        )

        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(tmp_path / "routing.yaml"))

        result = await handle_intake_compute_routing({"start": True}, _CTX)
        session_id = result["session_id"]

        for q in _INTAKE_QUESTIONS:
            answer = "none" if q["type"] == "text" else "yes"
            # Commit question: answer no (don't commit).
            if q["id"] == "q20_commit":
                answer = "no"
            result = await handle_intake_compute_routing(
                {"session_id": session_id, "answer": answer}, _CTX
            )

        assert result["status"] == "ok"
        assert result["complete"] is True
        assert result["rules_written"] is False
        assert not (tmp_path / "routing.yaml").exists()

    @pytest.mark.anyio
    async def test_full_interview_with_commit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Full 20-question run with commit=yes writes the config file."""
        from core.gateway.builtin_handlers import (
            _INTAKE_QUESTIONS,
            handle_intake_compute_routing,
        )

        routing_file = tmp_path / "routing.yaml"
        monkeypatch.setenv("COMPUTE_ROUTING_CONFIG", str(routing_file))

        result = await handle_intake_compute_routing({"start": True}, _CTX)
        session_id = result["session_id"]

        for q in _INTAKE_QUESTIONS:
            answer = "none" if q["type"] == "text" else "yes"
            result = await handle_intake_compute_routing(
                {"session_id": session_id, "answer": answer}, _CTX
            )

        assert result["status"] == "ok"
        assert result["complete"] is True
        assert result["rules_written"] is True
        assert routing_file.exists()
        saved = yaml.safe_load(routing_file.read_text())
        assert isinstance(saved["rules"], list)
        assert len(saved["rules"]) > 0


# ---------------------------------------------------------------------------
# get_npu_status
# ---------------------------------------------------------------------------


class TestGetNpuStatus:
    """Tests for the get_npu_status handler."""

    @pytest.mark.anyio
    async def test_xrt_smi_not_installed_no_driver(self) -> None:
        """When xrt-smi is absent and amdxdna sysfs is missing, reports both deps."""
        from core.gateway.builtin_handlers import handle_get_npu_status

        with (
            patch(
                "core.gateway.builtin_handlers._anyio.run_process",
                side_effect=FileNotFoundError,
            ),
            patch(
                "core.gateway.builtin_handlers._anyio.to_thread.run_sync",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await handle_get_npu_status({}, _CTX)

        assert result["status"] == "ok"
        assert result["experimental"] is True
        assert "error" in result
        assert result["driver_loaded"] is False

    @pytest.mark.anyio
    async def test_xrt_smi_not_installed_driver_loaded(self) -> None:
        """xrt-smi absent but amdxdna driver loaded → suggests installing XRT."""
        from core.gateway.builtin_handlers import handle_get_npu_status

        with (
            patch(
                "core.gateway.builtin_handlers._anyio.run_process",
                side_effect=FileNotFoundError,
            ),
            patch(
                "core.gateway.builtin_handlers._anyio.to_thread.run_sync",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await handle_get_npu_status({}, _CTX)

        assert result["driver_loaded"] is True
        assert "xrt" in result["error"].lower()

    @pytest.mark.anyio
    async def test_xrt_smi_returns_json(self) -> None:
        """Valid xrt-smi JSON is parsed and returned under 'npu' key."""
        from core.gateway.builtin_handlers import handle_get_npu_status

        fake_npu = {"aie_metadata": {"device_class": "AIE2PS", "cols": 5}}

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, json.dumps(fake_npu).encode())),
        ):
            result = await handle_get_npu_status({}, _CTX)

        assert result["status"] == "ok"
        assert result["npu"] == fake_npu
        assert result["source"] == "xrt-smi"

    @pytest.mark.anyio
    async def test_xrt_smi_no_device(self) -> None:
        """xrt-smi 'no device' stderr → suggests loading amdxdna module."""
        from core.gateway.builtin_handlers import handle_get_npu_status

        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(
                return_value=_make_completed(1, b"", b"Error: no device found")
            ),
        ):
            result = await handle_get_npu_status({}, _CTX)

        assert "amdxdna" in result["error"].lower()


# ---------------------------------------------------------------------------
# _build_routing_rules (unit test for intake rule builder)
# ---------------------------------------------------------------------------


class TestBuildRoutingRules:
    """Unit tests for the _build_routing_rules helper."""

    def test_all_yes_produces_rules(self) -> None:
        """All-yes answers generate a non-empty rule list."""
        from core.gateway.builtin_handlers import _INTAKE_QUESTIONS, _build_routing_rules

        answers = {q["id"]: "yes" for q in _INTAKE_QUESTIONS}
        answers["q11_extra_process_names"] = "none"
        rules = _build_routing_rules(answers)
        assert len(rules) > 0

    def test_no_gaming_no_game_rule(self) -> None:
        """When q01_gaming_primary=no, no gaming_process_nvidia rule is created."""
        from core.gateway.builtin_handlers import _INTAKE_QUESTIONS, _build_routing_rules

        answers = {q["id"]: "no" for q in _INTAKE_QUESTIONS}
        answers["q11_extra_process_names"] = "none"
        rules = _build_routing_rules(answers)
        rule_ids = [r["id"] for r in rules]
        assert "gaming_process_nvidia" not in rule_ids

    def test_cpu_fallback_rule_present_when_requested(self) -> None:
        """q08_cpu_fallback=yes adds a cpu_fallback rule."""
        from core.gateway.builtin_handlers import _INTAKE_QUESTIONS, _build_routing_rules

        answers = {q["id"]: "no" for q in _INTAKE_QUESTIONS}
        answers["q11_extra_process_names"] = "none"
        answers["q08_cpu_fallback"] = "yes"
        rules = _build_routing_rules(answers)
        assert any(r["id"] == "cpu_fallback" for r in rules)

    def test_extra_process_names_included(self) -> None:
        """Extra process names from q11 are added to the gaming rule."""
        from core.gateway.builtin_handlers import _INTAKE_QUESTIONS, _build_routing_rules

        answers = {q["id"]: "no" for q in _INTAKE_QUESTIONS}
        answers["q01_gaming_primary"] = "yes"
        answers["q10_extra_game_processes"] = "yes"
        answers["q11_extra_process_names"] = "eldenring.exe, GenshinImpact.exe"
        rules = _build_routing_rules(answers)
        gaming_rule = next((r for r in rules if r["id"] == "gaming_process_nvidia"), None)
        assert gaming_rule is not None
        assert "eldenring.exe" in gaming_rule["trigger"]["process_names"]
        assert "GenshinImpact.exe" in gaming_rule["trigger"]["process_names"]

    def test_all_no_produces_minimal_rules(self) -> None:
        """All-no answers produce very few rules (just transcription + rag fallback)."""
        from core.gateway.builtin_handlers import _INTAKE_QUESTIONS, _build_routing_rules

        answers = {q["id"]: "no" for q in _INTAKE_QUESTIONS}
        answers["q11_extra_process_names"] = "none"
        rules = _build_routing_rules(answers)
        # Should not include gaming or GPU-specific rules.
        rule_ids = [r["id"] for r in rules]
        assert "gaming_process_nvidia" not in rule_ids
        assert "cpu_fallback" not in rule_ids
