"""Custom exception hierarchy for OsMEN-OC.

All public API errors must inherit from :class:`OsMENError`.
"""

from __future__ import annotations


class OsMENError(Exception):
    """Base exception for all OsMEN-OC errors."""


class ConfigError(OsMENError):
    """Raised when configuration is missing or invalid."""


class ApprovalRequiredError(OsMENError):
    """Raised when a tool invocation requires human approval."""


class RateLimitError(OsMENError):
    """Raised on LLM provider rate-limit (GLM error 1302)."""
