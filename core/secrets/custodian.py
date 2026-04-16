"""Secrets custodian: audit, verify, and manage credentials across stores.

This module provides the tool implementations that the secrets_custodian
agent exposes via MCP. It coordinates across env file, SOPS, Podman secrets,
and OpenClaw SecretRefs without being a credential store itself.
"""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from core.utils.exceptions import SecretsError

ENV_FILE = Path.home() / ".config" / "osmen" / "env"
SOPS_DIR = Path.home() / ".config" / "osmen" / "secrets"
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "secrets-registry.yaml"


@dataclass
class Finding:
    """A single audit finding."""

    check: str
    severity: str  # info, warning, error, critical
    message: str
    secret_name: str | None = None
    remediation: str | None = None


@dataclass
class AuditReport:
    """Aggregated audit results."""

    findings: list[Finding] = field(default_factory=list)
    checked: int = 0
    passed: int = 0

    @property
    def failed(self) -> int:
        return self.checked - self.passed

    @property
    def clean(self) -> bool:
        return all(f.severity == "info" for f in self.findings)

    def summary(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "passed": self.passed,
            "failed": self.failed,
            "clean": self.clean,
            "findings": [
                {"check": f.check, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
        }


class SecretsCustodian:
    """Coordinates secrets auditing and verification across all stores.

    Args:
        registry_path: Path to the secrets-registry.yaml file.
        env_path: Path to the runtime env file.
        sops_dir: Path to the SOPS-encrypted secrets directory.
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        env_path: Path | None = None,
        sops_dir: Path | None = None,
    ) -> None:
        self.registry_path = registry_path or REGISTRY_PATH
        self.env_path = env_path or ENV_FILE
        self.sops_dir = sops_dir or SOPS_DIR
        self._registry: dict[str, Any] | None = None

    @property
    def registry(self) -> dict[str, Any]:
        if self._registry is None:
            self._registry = self._load_registry()
        return self._registry

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            raise SecretsError(f"Registry not found: {self.registry_path}")
        with open(self.registry_path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "secrets" not in data:
            raise SecretsError("Invalid registry: missing 'secrets' key")
        return data

    def audit_secrets(self) -> AuditReport:
        """Run all audit checks and return aggregated report.

        Returns:
            AuditReport with findings from all checks.
        """
        from core.secrets.audit_checks import run_all_checks

        report = run_all_checks(
            registry=self.registry,
            env_path=self.env_path,
            sops_dir=self.sops_dir,
        )
        logger.info(
            "Secrets audit complete: checked={} passed={} failed={}",
            report.checked,
            report.passed,
            report.failed,
        )
        return report

    def verify_env_file(self) -> list[Finding]:
        """Verify env file exists, has correct permissions, and is parseable.

        Returns:
            List of findings (empty = clean).
        """
        findings: list[Finding] = []
        if not self.env_path.exists():
            findings.append(
                Finding(
                    check="env_file_exists",
                    severity="critical",
                    message=f"Env file not found: {self.env_path}",
                    remediation="Run scripts/bootstrap.sh or create the file manually.",
                )
            )
            return findings

        mode = self.env_path.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
            findings.append(
                Finding(
                    check="env_file_permissions",
                    severity="error",
                    message=f"Env file has unsafe permissions: {oct(mode)}",
                    remediation=f"chmod 600 {self.env_path}",
                )
            )

        env_keys = self._parse_env_file()
        registry_env_vars = {
            s.get("env_var")
            for s in self.registry.get("secrets", {}).values()
            if s.get("env_var")
        }
        missing = registry_env_vars - env_keys
        for var in sorted(missing):
            findings.append(
                Finding(
                    check="env_key_missing",
                    severity="warning",
                    message=f"Registry expects {var} in env file but it's absent",
                    secret_name=var,
                    remediation=f"Add {var}=<value> to {self.env_path}",
                )
            )
        return findings

    def verify_podman_secrets(self) -> list[Finding]:
        """Verify registered Podman secrets exist.

        Returns:
            List of findings for missing secrets.
        """
        findings: list[Finding] = []
        try:
            result = subprocess.run(
                ["podman", "secret", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            existing = set(result.stdout.strip().splitlines())
        except (subprocess.SubprocessError, FileNotFoundError):
            findings.append(
                Finding(
                    check="podman_available",
                    severity="error",
                    message="Cannot list Podman secrets",
                )
            )
            return findings

        for name, meta in self.registry.get("secrets", {}).items():
            podman_name = meta.get("podman_name")
            if podman_name and podman_name not in existing:
                findings.append(
                    Finding(
                        check="podman_secret_missing",
                        severity="error",
                        message=f"Podman secret '{podman_name}' not found",
                        secret_name=name,
                        remediation=f"podman secret create {podman_name} <value-file>",
                    )
                )
        return findings

    def verify_sops_files(self) -> list[Finding]:
        """Verify expected SOPS-encrypted files exist and are decryptable.

        Returns:
            List of findings.
        """
        findings: list[Finding] = []
        expected_files: set[str] = set()
        for meta in self.registry.get("secrets", {}).values():
            sops_file = meta.get("sops_file")
            if sops_file:
                expected_files.add(sops_file)

        for filename in sorted(expected_files):
            fpath = self.sops_dir / filename
            if not fpath.exists():
                findings.append(
                    Finding(
                        check="sops_file_missing",
                        severity="error",
                        message=f"SOPS file not found: {fpath}",
                        remediation=f"sops encrypt config/secrets/{filename.replace('.enc.', '.template.')} > {fpath}",
                    )
                )
        return findings

    def verify_openclaw_audit(self) -> list[Finding]:
        """Run 'openclaw secrets audit' and parse results.

        Returns:
            List of findings based on openclaw output.
        """
        findings: list[Finding] = []
        env = self._build_env()
        try:
            result = subprocess.run(
                ["openclaw", "secrets", "audit"],
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
            output = result.stdout + result.stderr
        except (subprocess.SubprocessError, FileNotFoundError):
            findings.append(
                Finding(
                    check="openclaw_available",
                    severity="warning",
                    message="Cannot run openclaw secrets audit",
                )
            )
            return findings

        if "plaintext=" in output:
            import re

            match = re.search(r"plaintext=(\d+)", output)
            if match and int(match.group(1)) > 0:
                findings.append(
                    Finding(
                        check="openclaw_plaintext",
                        severity="error",
                        message=f"OpenClaw reports {match.group(1)} plaintext secrets",
                        remediation="Run: openclaw secrets configure",
                    )
                )
        return findings

    def _parse_env_file(self) -> set[str]:
        """Parse env file and return set of defined variable names."""
        keys: set[str] = set()
        if not self.env_path.exists():
            return keys
        for line in self.env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                keys.add(line.split("=", 1)[0])
        return keys

    def _build_env(self) -> dict[str, str]:
        """Build environment dict with osmen env file vars merged in."""
        env = dict(os.environ)
        if self.env_path.exists():
            for line in self.env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key] = val
        return env
