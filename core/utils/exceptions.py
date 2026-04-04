"""Exception hierarchy for OsMEN-OC.

All exceptions are rooted at :class:`OsMENError`.
"""

from __future__ import annotations


class OsMENError(Exception):
    """Base exception for all OsMEN-OC errors.

    Args:
        message: Human-readable error description.
        correlation_id: Optional trace identifier for distributed workflows.
    """

    def __init__(self, message: str, correlation_id: str | None = None) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class ConfigError(OsMENError):
    """Raised when configuration loading or validation fails."""


class ManifestError(OsMENError):
    """Raised when an agent manifest is invalid or cannot be loaded."""


class RegistrationError(OsMENError):
    """Raised when MCP tool registration fails."""


class EventBusError(OsMENError):
    """Raised when the event bus cannot publish or consume a message."""


class ApprovalError(OsMENError):
    """Raised when an approval gate rejects or fails to evaluate a request."""


class AuditError(OsMENError):
    """Raised when an audit trail operation fails."""


class PipelineError(OsMENError):
    """Raised when pipeline loading or step execution fails."""
