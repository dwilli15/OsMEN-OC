"""Tests for core.approval.gate."""

from __future__ import annotations

import anyio
import pytest

from core.approval.gate import (
    ApprovalGate,
    ApprovalOutcome,
    ApprovalRequest,
    RiskLevel,
)
from core.utils.exceptions import ApprovalError


def _make_request(risk: RiskLevel, tool: str = "test_tool") -> ApprovalRequest:
    return ApprovalRequest(
        tool_name=tool,
        agent_id="test_agent",
        risk_level=risk,
        parameters={"key": "value"},
    )


# ---------------------------------------------------------------------------
# Low risk — auto-approve, not flagged for summary
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_low_risk_auto_approved():
    """Low-risk requests are approved automatically."""
    gate = ApprovalGate()
    result = await gate.evaluate(_make_request(RiskLevel.LOW))
    assert result.outcome == ApprovalOutcome.APPROVED
    assert result.flagged_for_summary is False


# ---------------------------------------------------------------------------
# Medium risk — auto-approve, flagged for daily summary
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_medium_risk_auto_approved_and_flagged():
    """Medium-risk requests are approved and flagged for daily summary."""
    gate = ApprovalGate()
    result = await gate.evaluate(_make_request(RiskLevel.MEDIUM))
    assert result.outcome == ApprovalOutcome.APPROVED
    assert result.flagged_for_summary is True


# ---------------------------------------------------------------------------
# High risk — requires human approval
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_high_risk_approved_by_callback():
    """High-risk requests are approved when the callback returns True."""

    async def approve(_req):
        return True

    gate = ApprovalGate(approval_callback=approve)
    result = await gate.evaluate(_make_request(RiskLevel.HIGH))
    assert result.outcome == ApprovalOutcome.APPROVED


@pytest.mark.anyio
async def test_high_risk_denied_by_callback():
    """High-risk requests are denied when the callback returns False."""

    async def deny(_req):
        return False

    gate = ApprovalGate(approval_callback=deny)
    result = await gate.evaluate(_make_request(RiskLevel.HIGH))
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.anyio
async def test_high_risk_denied_on_timeout():
    """High-risk requests are denied when the callback times out."""

    async def slow(_req):
        await anyio.sleep(999)
        return True

    gate = ApprovalGate(approval_callback=slow)
    request = _make_request(RiskLevel.HIGH)
    # Patch timeout to 0.01s so the test runs fast
    from core.approval import gate as gate_module

    original_timeout = gate_module.HIGH_RISK_TIMEOUT_SECONDS
    gate_module.HIGH_RISK_TIMEOUT_SECONDS = 0.01
    try:
        result = await gate.evaluate(request)
    finally:
        gate_module.HIGH_RISK_TIMEOUT_SECONDS = original_timeout

    assert result.outcome == ApprovalOutcome.DENIED
    assert "timed out" in result.reason


@pytest.mark.anyio
async def test_high_risk_denied_without_callback():
    """High-risk requests are denied when no callback is configured."""
    gate = ApprovalGate()
    result = await gate.evaluate(_make_request(RiskLevel.HIGH))
    assert result.outcome == ApprovalOutcome.DENIED


# ---------------------------------------------------------------------------
# Critical risk — blocks until human confirms, never times out
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_critical_risk_approved_by_callback():
    """Critical-risk requests are approved when the callback returns True."""

    async def approve(_req):
        return True

    gate = ApprovalGate(approval_callback=approve)
    result = await gate.evaluate(_make_request(RiskLevel.CRITICAL))
    assert result.outcome == ApprovalOutcome.APPROVED


@pytest.mark.anyio
async def test_critical_risk_denied_without_callback():
    """Critical-risk requests are denied when no callback is configured."""
    gate = ApprovalGate()
    result = await gate.evaluate(_make_request(RiskLevel.CRITICAL))
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.anyio
async def test_callback_exception_raises_approval_error():
    """Callback exceptions are re-raised as ApprovalError."""

    async def boom(_req):
        raise RuntimeError("callback crashed")

    gate = ApprovalGate(approval_callback=boom)
    with pytest.raises(ApprovalError):
        await gate.evaluate(_make_request(RiskLevel.HIGH))


# ---------------------------------------------------------------------------
# Adaptive risk overrides (D4)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_risk_override_downgrades_high_to_low():
    """An override downgrades HIGH → LOW so the tool auto-approves."""
    gate = ApprovalGate()  # no callback — HIGH would normally deny
    gate.override_risk("agent_x", "dangerous_tool", RiskLevel.LOW)

    request = ApprovalRequest(
        tool_name="dangerous_tool",
        agent_id="agent_x",
        risk_level=RiskLevel.HIGH,
        parameters={},
    )
    result = await gate.evaluate(request)
    assert result.outcome == ApprovalOutcome.APPROVED


@pytest.mark.anyio
async def test_risk_override_upgrades_low_to_high_denies_without_callback():
    """An override escalates LOW → HIGH; with no callback the tool is denied."""
    gate = ApprovalGate()  # no callback
    gate.override_risk("agent_y", "safe_tool", RiskLevel.HIGH)

    request = ApprovalRequest(
        tool_name="safe_tool",
        agent_id="agent_y",
        risk_level=RiskLevel.LOW,
        parameters={},
    )
    result = await gate.evaluate(request)
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.anyio
async def test_risk_override_scoped_to_agent_tool_pair():
    """Override on (agent_a, tool_x) does not affect (agent_b, tool_x)."""
    gate = ApprovalGate()
    gate.override_risk("agent_a", "shared_tool", RiskLevel.LOW)

    request_b = ApprovalRequest(
        tool_name="shared_tool",
        agent_id="agent_b",
        risk_level=RiskLevel.HIGH,
        parameters={},
    )
    result = await gate.evaluate(request_b)
    # agent_b has no override — still HIGH → denied without callback
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.anyio
async def test_clear_risk_override_restores_declared_level():
    """clear_risk_override removes the override so declared risk is used again."""
    gate = ApprovalGate()
    gate.override_risk("agent_z", "tool_q", RiskLevel.LOW)
    gate.clear_risk_override("agent_z", "tool_q")

    request = ApprovalRequest(
        tool_name="tool_q",
        agent_id="agent_z",
        risk_level=RiskLevel.HIGH,
        parameters={},
    )
    result = await gate.evaluate(request)
    # Override cleared — HIGH without callback → denied
    assert result.outcome == ApprovalOutcome.DENIED
