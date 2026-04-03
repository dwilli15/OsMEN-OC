"""Approval gate: risk-assessed tool invocation policy.

Every tool call in OsMEN-OC passes through :func:`ApprovalGate.evaluate`
before execution.  The gate enforces a four-tier policy:

+----------+----------------------------------------------------------+
| Risk     | Policy                                                   |
+==========+==========================================================+
| low      | Auto-approve and log.                                    |
+----------+----------------------------------------------------------+
| medium   | Auto-approve, log, and flag for daily summary.           |
+----------+----------------------------------------------------------+
| high     | Queue for human approval (timeout: 5 min). Blocked until |
|          | approved or timed out.  Default on timeout: **deny**.    |
+----------+----------------------------------------------------------+
| critical | Block indefinitely until explicit human confirmation via |
|          | OpenClaw.  Never auto-approved.                          |
+----------+----------------------------------------------------------+
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

import anyio
from loguru import logger

from core.utils.exceptions import ApprovalError

# Seconds to wait for a human response on HIGH-risk requests before denying
HIGH_RISK_TIMEOUT_SECONDS = 300


class RiskLevel(StrEnum):
    """Enumerated risk levels for tool invocations.

    Attributes:
        LOW: Read-only or observational operations.
        MEDIUM: Write operations or data transfers.
        HIGH: Destructive or privileged operations.
        CRITICAL: Security-sensitive or irreversible operations.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalOutcome(StrEnum):
    """Result returned by the approval gate.

    Attributes:
        APPROVED: The request may proceed.
        DENIED: The request must not proceed.
        PENDING: Awaiting human decision (internal transient state).
    """

    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"


@dataclass
class ApprovalRequest:
    """Encapsulates the context of a single gate evaluation.

    Attributes:
        tool_name: The tool being invoked.
        agent_id: Agent requesting the invocation.
        risk_level: Risk classification of the tool.
        parameters: Parameters that will be passed to the tool.
        correlation_id: Optional trace identifier.
        requested_at: UTC timestamp of the request.
    """

    tool_name: str
    agent_id: str
    risk_level: RiskLevel
    parameters: dict
    correlation_id: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ApprovalResult:
    """Outcome of a gate evaluation.

    Attributes:
        outcome: The gate decision.
        request: The original request.
        decided_at: UTC timestamp of the decision.
        reason: Human-readable explanation of the decision.
        flagged_for_summary: True when the result should appear in the daily summary.
    """

    outcome: ApprovalOutcome
    request: ApprovalRequest
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    flagged_for_summary: bool = False


# Type alias for the async callback used to request human approval
ApprovalCallback = Callable[[ApprovalRequest], Awaitable[bool]]


class ApprovalGate:
    """Evaluates tool invocation requests against a four-tier risk policy.

    For HIGH and CRITICAL risk levels the gate requires an external
    *approval_callback* — a coroutine that forwards the request to a human
    operator (e.g. via OpenClaw → Telegram) and awaits their decision.

    Args:
        approval_callback: Async callable that receives an
            :class:`ApprovalRequest` and returns ``True`` (approve) or
            ``False`` (deny).  Required for HIGH/CRITICAL requests.  If not
            provided those risk levels will always be denied.
    """

    def __init__(
        self,
        approval_callback: ApprovalCallback | None = None,
    ) -> None:
        self._callback = approval_callback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(self, request: ApprovalRequest) -> ApprovalResult:
        """Evaluate an invocation request and return a gate decision.

        Args:
            request: The tool invocation context to evaluate.

        Returns:
            An :class:`ApprovalResult` whose ``outcome`` field indicates
            whether the tool may execute.

        Raises:
            ApprovalError: If the gate encounters an unexpected internal error.
        """
        match request.risk_level:
            case RiskLevel.LOW:
                return self._auto_approve(request, flagged=False)
            case RiskLevel.MEDIUM:
                return self._auto_approve(request, flagged=True)
            case RiskLevel.HIGH:
                return await self._human_approve(
                    request,
                    timeout=HIGH_RISK_TIMEOUT_SECONDS,
                )
            case RiskLevel.CRITICAL:
                return await self._human_approve(request, timeout=None)
            case _:
                raise ApprovalError(
                    f"Unknown risk level: {request.risk_level}",
                    correlation_id=request.correlation_id,
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auto_approve(
        self,
        request: ApprovalRequest,
        *,
        flagged: bool,
    ) -> ApprovalResult:
        """Approve automatically with optional daily-summary flag.

        Args:
            request: Gate evaluation context.
            flagged: When ``True`` the result is marked for the daily summary.

        Returns:
            Approved :class:`ApprovalResult`.
        """
        logger.info(
            "Auto-approved tool={} agent={} risk={}",
            request.tool_name,
            request.agent_id,
            request.risk_level.value,
        )
        return ApprovalResult(
            outcome=ApprovalOutcome.APPROVED,
            request=request,
            reason="auto-approved",
            flagged_for_summary=flagged,
        )

    async def _human_approve(
        self,
        request: ApprovalRequest,
        *,
        timeout: float | None,
    ) -> ApprovalResult:
        """Request human approval, with an optional timeout.

        HIGH-risk requests time out after :data:`HIGH_RISK_TIMEOUT_SECONDS`
        and default to **deny**.  CRITICAL requests block indefinitely (no
        timeout) until the human responds.

        Args:
            request: Gate evaluation context.
            timeout: Seconds to wait for human response.  ``None`` means
                wait indefinitely (CRITICAL policy).

        Returns:
            :class:`ApprovalResult` reflecting the human decision or timeout.
        """
        if self._callback is None:
            logger.warning(
                "No approval_callback configured — denying tool={} risk={}",
                request.tool_name,
                request.risk_level.value,
            )
            return ApprovalResult(
                outcome=ApprovalOutcome.DENIED,
                request=request,
                reason="no approval callback configured",
            )

        logger.info(
            "Requesting human approval tool={} agent={} risk={} timeout={}s",
            request.tool_name,
            request.agent_id,
            request.risk_level.value,
            timeout,
        )

        try:
            if timeout is not None:
                with anyio.fail_after(timeout):
                    approved = await self._callback(request)
            else:
                approved = await self._callback(request)
        except TimeoutError:
            logger.warning(
                "Approval timed out after {}s — denying tool={} agent={}",
                timeout,
                request.tool_name,
                request.agent_id,
            )
            return ApprovalResult(
                outcome=ApprovalOutcome.DENIED,
                request=request,
                reason=f"approval timed out after {timeout}s",
            )
        except Exception as exc:
            raise ApprovalError(
                f"Approval callback raised an unexpected error: {exc}",
                correlation_id=request.correlation_id,
            ) from exc

        outcome = ApprovalOutcome.APPROVED if approved else ApprovalOutcome.DENIED
        logger.info(
            "Human decision: {} tool={} agent={}",
            outcome.value,
            request.tool_name,
            request.agent_id,
        )
        return ApprovalResult(
            outcome=outcome,
            request=request,
            reason="human decision",
        )
