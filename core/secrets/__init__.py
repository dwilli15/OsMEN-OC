"""Secrets management for OsMEN-OC.

Provides audit, verification, and rotation utilities that work across
all credential stores: env file, SOPS, Podman secrets, OpenClaw SecretRefs,
and CLI keystores.
"""

from __future__ import annotations

from core.secrets.custodian import SecretsCustodian
from core.secrets.audit_checks import run_all_checks

__all__ = ["SecretsCustodian", "run_all_checks"]
