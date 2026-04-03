"""Audit subpackage: immutable append-only trail with archive support."""

from core.audit.trail import AuditRecord, AuditTrail

__all__ = ["AuditTrail", "AuditRecord"]
