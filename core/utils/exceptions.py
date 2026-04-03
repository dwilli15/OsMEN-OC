"""Custom exception hierarchy for OsMEN-OC."""

from __future__ import annotations


class OsMENError(Exception):
    """Base exception for all OsMEN-OC errors.

    All domain-specific exceptions should subclass this so callers can
    catch the entire family with a single ``except OsMENError``.

    Args:
        message: Human-readable error description.
        correlation_id: Optional trace/correlation identifier.
    """

    def __init__(self, message: str, correlation_id: str | None = None) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class EventBusError(OsMENError):
    """Raised when the event bus cannot publish or consume a message."""


class ApprovalError(OsMENError):
    """Raised when an approval gate rejects or fails to evaluate a request."""


class AuditError(OsMENError):
    """Raised when an audit trail operation fails."""
