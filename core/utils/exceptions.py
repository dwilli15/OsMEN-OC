"""Exception hierarchy for OsMEN-OC.

All exceptions are rooted at :class:`OsMENError`.
"""

from __future__ import annotations


class OsMENError(Exception):
    """Base exception for all OsMEN-OC errors."""


class ConfigError(OsMENError):
    """Raised when configuration loading or validation fails."""


class ManifestError(OsMENError):
    """Raised when an agent manifest is invalid or cannot be loaded."""


class RegistrationError(OsMENError):
    """Raised when MCP tool registration fails."""


class ApprovalError(OsMENError):
    """Raised when an operation is blocked pending human approval."""
