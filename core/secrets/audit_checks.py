"""Individual audit checks for the secrets custodian.

Each check function takes the registry dict and relevant paths, returns
a list of Findings. ``run_all_checks`` aggregates them into an AuditReport.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from core.secrets.custodian import AuditReport, Finding


def check_env_permissions(env_path: Path) -> list[Finding]:
    """Verify env file permissions are owner-only (600)."""
    if not env_path.exists():
        return [
            Finding(
                check="env_permissions",
                severity="critical",
                message=f"Env file missing: {env_path}",
            )
        ]
    mode = env_path.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
        return [
            Finding(
                check="env_permissions",
                severity="error",
                message=f"Env file permissions too open: {oct(mode)}",
                remediation=f"chmod 600 {env_path}",
            )
        ]
    return []


def check_env_completeness(
    registry: dict[str, Any], env_path: Path
) -> list[Finding]:
    """Check all registry-declared env vars exist in the env file."""
    findings: list[Finding] = []
    env_keys: set[str] = set()
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                env_keys.add(line.split("=", 1)[0])

    for name, meta in registry.get("secrets", {}).items():
        if meta.get("status") == "not-provisioned":
            continue
        env_var = meta.get("env_var")
        if env_var and env_var not in env_keys:
            findings.append(
                Finding(
                    check="env_completeness",
                    severity="warning",
                    message=f"{env_var} declared in registry but missing from env file",
                    secret_name=name,
                )
            )
    return findings


def check_podman_secrets(registry: dict[str, Any]) -> list[Finding]:
    """Verify all registry-declared Podman secrets exist."""
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
        return [
            Finding(
                check="podman_secrets",
                severity="error",
                message="Cannot list Podman secrets (podman unavailable or errored)",
            )
        ]

    for name, meta in registry.get("secrets", {}).items():
        podman_name = meta.get("podman_name")
        if podman_name and podman_name not in existing:
            findings.append(
                Finding(
                    check="podman_secrets",
                    severity="error",
                    message=f"Podman secret '{podman_name}' missing",
                    secret_name=name,
                    remediation=f"podman secret create {podman_name} <value-file>",
                )
            )
    return findings


def check_sops_files(
    registry: dict[str, Any], sops_dir: Path
) -> list[Finding]:
    """Verify expected SOPS-encrypted files exist."""
    findings: list[Finding] = []
    expected: set[str] = set()
    for meta in registry.get("secrets", {}).values():
        sops_file = meta.get("sops_file")
        if sops_file:
            expected.add(sops_file)

    for filename in sorted(expected):
        if not (sops_dir / filename).exists():
            findings.append(
                Finding(
                    check="sops_files",
                    severity="error",
                    message=f"SOPS file missing: {sops_dir / filename}",
                )
            )
    return findings


def check_sops_dir_permissions(sops_dir: Path) -> list[Finding]:
    """Verify SOPS directory is owner-only (700)."""
    if not sops_dir.exists():
        return [
            Finding(
                check="sops_dir_permissions",
                severity="error",
                message=f"SOPS directory missing: {sops_dir}",
            )
        ]
    mode = sops_dir.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH):
        return [
            Finding(
                check="sops_dir_permissions",
                severity="error",
                message=f"SOPS dir permissions too open: {oct(mode)}",
                remediation=f"chmod 700 {sops_dir}",
            )
        ]
    return []


def check_git_staged_secrets() -> list[Finding]:
    """Scan git index for common secret patterns."""
    findings: list[Finding] = []
    patterns = [
        r"ghp_[A-Za-z0-9]{36}",
        r"sk-[A-Za-z0-9]{20,}",
        r"AGE-SECRET-KEY-",
        r"AKIA[A-Z0-9]{16}",
    ]
    try:
        for pattern in patterns:
            result = subprocess.run(
                ["git", "log", "--all", "-p", "-G", pattern, "--oneline", "--max-count=1"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout.strip():
                findings.append(
                    Finding(
                        check="git_history_secrets",
                        severity="critical",
                        message=f"Secret pattern '{pattern}' found in git history",
                        remediation="Consider git-filter-repo to purge the commit",
                    )
                )
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.debug("git not available for history scan")
    return findings


def check_template_drift(
    registry: dict[str, Any], sops_dir: Path
) -> list[Finding]:
    """Check that template files have corresponding encrypted files."""
    findings: list[Finding] = []
    templates_dir = Path(__file__).resolve().parents[2] / "config" / "secrets"
    if not templates_dir.exists():
        return findings

    for tmpl in sorted(templates_dir.glob("*.template.yaml")):
        enc_name = tmpl.name.replace(".template.", ".enc.")
        if not (sops_dir / enc_name).exists():
            findings.append(
                Finding(
                    check="template_drift",
                    severity="warning",
                    message=f"Template {tmpl.name} has no encrypted counterpart {enc_name}",
                    remediation=f"sops --encrypt {tmpl} > {sops_dir / enc_name}",
                )
            )
    return findings


def run_all_checks(
    registry: dict[str, Any],
    env_path: Path,
    sops_dir: Path,
) -> AuditReport:
    """Execute all audit checks and aggregate into a report.

    Args:
        registry: Parsed secrets-registry.yaml data.
        env_path: Path to the runtime env file.
        sops_dir: Path to the SOPS-encrypted secrets directory.

    Returns:
        AuditReport with all findings aggregated.
    """
    report = AuditReport()
    checks = [
        ("env_permissions", lambda: check_env_permissions(env_path)),
        ("env_completeness", lambda: check_env_completeness(registry, env_path)),
        ("podman_secrets", lambda: check_podman_secrets(registry)),
        ("sops_files", lambda: check_sops_files(registry, sops_dir)),
        ("sops_dir_permissions", lambda: check_sops_dir_permissions(sops_dir)),
        ("template_drift", lambda: check_template_drift(registry, sops_dir)),
        ("git_history", lambda: check_git_staged_secrets()),
    ]

    for check_name, check_fn in checks:
        report.checked += 1
        try:
            findings = check_fn()
            report.findings.extend(findings)
            if not findings:
                report.passed += 1
        except Exception as exc:
            logger.error("Check '{}' failed: {}", check_name, exc)
            report.findings.append(
                Finding(
                    check=check_name,
                    severity="error",
                    message=f"Check raised an exception: {exc}",
                )
            )
    return report
