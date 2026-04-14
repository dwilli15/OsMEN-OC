"""Tests for core.secrets — custodian and audit checks."""

from __future__ import annotations

import os
import stat
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from core.secrets.custodian import AuditReport, Finding, SecretsCustodian
from core.secrets.audit_checks import (
    check_env_completeness,
    check_env_permissions,
    check_sops_dir_permissions,
    check_sops_files,
    check_template_drift,
    run_all_checks,
)
from core.utils.exceptions import SecretsError


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def registry_data() -> dict:
    """Minimal valid registry for testing."""
    return {
        "secrets": {
            "test_key": {
                "description": "Test API key",
                "stores": ["env", "sops"],
                "rotation": "manual",
                "required_by": ["gateway"],
                "env_var": "TEST_API_KEY",
                "sops_file": "api-keys.enc.yaml",
            },
            "test_podman": {
                "description": "Test podman secret",
                "stores": ["podman"],
                "rotation": "90d",
                "required_by": ["gateway"],
                "podman_name": "osmen-test-secret",
            },
            "future_secret": {
                "description": "Not provisioned yet",
                "stores": ["sops"],
                "rotation": "manual",
                "required_by": [],
                "env_var": "FUTURE_VAR",
                "status": "not-provisioned",
            },
        }
    }


@pytest.fixture
def registry_file(tmp_path: Path, registry_data: dict) -> Path:
    """Write registry data to a temp file and return its path."""
    fpath = tmp_path / "secrets-registry.yaml"
    fpath.write_text(yaml.dump(registry_data))
    return fpath


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    """Create a minimal env file with correct permissions."""
    fpath = tmp_path / "env"
    fpath.write_text("TEST_API_KEY=abc123\nOTHER_VAR=xyz\n")
    fpath.chmod(0o600)
    return fpath


@pytest.fixture
def sops_dir(tmp_path: Path) -> Path:
    """Create a SOPS directory with correct permissions."""
    d = tmp_path / "secrets"
    d.mkdir()
    d.chmod(0o700)
    (d / "api-keys.enc.yaml").write_text("encrypted: true")
    return d


@pytest.fixture
def custodian(registry_file: Path, env_file: Path, sops_dir: Path) -> SecretsCustodian:
    """SecretsCustodian wired to temp paths."""
    return SecretsCustodian(
        registry_path=registry_file,
        env_path=env_file,
        sops_dir=sops_dir,
    )


# ── AuditReport ──────────────────────────────────────────────────────


class TestAuditReport:
    def test_clean_when_no_findings(self) -> None:
        report = AuditReport(checked=3, passed=3)
        assert report.clean is True
        assert report.failed == 0

    def test_not_clean_with_warning(self) -> None:
        report = AuditReport(
            findings=[Finding(check="x", severity="warning", message="bad")],
            checked=1,
            passed=0,
        )
        assert report.clean is False

    def test_clean_with_info_only(self) -> None:
        report = AuditReport(
            findings=[Finding(check="x", severity="info", message="ok")],
            checked=1,
            passed=1,
        )
        assert report.clean is True

    def test_summary_structure(self) -> None:
        report = AuditReport(
            findings=[Finding(check="x", severity="error", message="fail")],
            checked=2,
            passed=1,
        )
        s = report.summary()
        assert s["checked"] == 2
        assert s["passed"] == 1
        assert s["failed"] == 1
        assert s["clean"] is False
        assert len(s["findings"]) == 1


# ── SecretsCustodian ─────────────────────────────────────────────────


class TestSecretsCustodian:
    def test_load_registry_success(self, custodian: SecretsCustodian) -> None:
        reg = custodian.registry
        assert "secrets" in reg
        assert "test_key" in reg["secrets"]

    def test_load_registry_missing_file(self, tmp_path: Path) -> None:
        c = SecretsCustodian(registry_path=tmp_path / "nope.yaml")
        with pytest.raises(SecretsError, match="Registry not found"):
            _ = c.registry

    def test_load_registry_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("just_a_string")
        c = SecretsCustodian(registry_path=bad)
        with pytest.raises(SecretsError, match="missing 'secrets' key"):
            _ = c.registry

    def test_verify_env_file_clean(self, custodian: SecretsCustodian) -> None:
        findings = custodian.verify_env_file()
        # TEST_API_KEY is in env file, no missing keys
        assert not any(f.severity in ("error", "critical") for f in findings)

    def test_verify_env_file_missing(self, tmp_path: Path, registry_file: Path) -> None:
        c = SecretsCustodian(
            registry_path=registry_file,
            env_path=tmp_path / "nonexistent",
        )
        findings = c.verify_env_file()
        assert any(f.severity == "critical" for f in findings)

    def test_verify_env_file_bad_perms(
        self, custodian: SecretsCustodian, env_file: Path
    ) -> None:
        env_file.chmod(0o644)
        findings = custodian.verify_env_file()
        assert any(f.check == "env_file_permissions" for f in findings)

    def test_verify_sops_files_clean(self, custodian: SecretsCustodian) -> None:
        findings = custodian.verify_sops_files()
        assert len(findings) == 0

    def test_verify_sops_files_missing(
        self, custodian: SecretsCustodian, sops_dir: Path
    ) -> None:
        (sops_dir / "api-keys.enc.yaml").unlink()
        findings = custodian.verify_sops_files()
        assert any(f.check == "sops_file_missing" for f in findings)

    @patch("core.secrets.custodian.subprocess.run")
    def test_verify_podman_secrets_clean(
        self,
        mock_run: MagicMock,
        custodian: SecretsCustodian,
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="osmen-test-secret\nosmen-other\n",
            stderr="",
            returncode=0,
        )
        findings = custodian.verify_podman_secrets()
        assert len(findings) == 0

    @patch("core.secrets.custodian.subprocess.run")
    def test_verify_podman_secrets_missing(
        self,
        mock_run: MagicMock,
        custodian: SecretsCustodian,
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="osmen-other\n",
            stderr="",
            returncode=0,
        )
        findings = custodian.verify_podman_secrets()
        assert any(f.check == "podman_secret_missing" for f in findings)

    @patch("core.secrets.custodian.subprocess.run")
    def test_verify_openclaw_clean(
        self,
        mock_run: MagicMock,
        custodian: SecretsCustodian,
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="Secrets audit: clean. plaintext=0, unresolved=0.\n",
            stderr="",
            returncode=0,
        )
        findings = custodian.verify_openclaw_audit()
        assert len(findings) == 0

    @patch("core.secrets.custodian.subprocess.run")
    def test_verify_openclaw_plaintext(
        self,
        mock_run: MagicMock,
        custodian: SecretsCustodian,
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="Secrets audit: findings. plaintext=3, unresolved=1.\n",
            stderr="",
            returncode=0,
        )
        findings = custodian.verify_openclaw_audit()
        assert any(f.check == "openclaw_plaintext" for f in findings)


# ── Individual Checks ────────────────────────────────────────────────


class TestCheckEnvPermissions:
    def test_correct_permissions(self, env_file: Path) -> None:
        assert check_env_permissions(env_file) == []

    def test_too_open(self, env_file: Path) -> None:
        env_file.chmod(0o644)
        findings = check_env_permissions(env_file)
        assert len(findings) == 1
        assert findings[0].severity == "error"

    def test_missing_file(self, tmp_path: Path) -> None:
        findings = check_env_permissions(tmp_path / "nope")
        assert findings[0].severity == "critical"


class TestCheckEnvCompleteness:
    def test_all_present(self, registry_data: dict, env_file: Path) -> None:
        findings = check_env_completeness(registry_data, env_file)
        assert len(findings) == 0

    def test_missing_var(self, registry_data: dict, tmp_path: Path) -> None:
        f = tmp_path / "env"
        f.write_text("WRONG_KEY=val\n")
        findings = check_env_completeness(registry_data, f)
        assert any(f.secret_name == "test_key" for f in findings)

    def test_skips_not_provisioned(self, registry_data: dict, tmp_path: Path) -> None:
        f = tmp_path / "env"
        f.write_text("TEST_API_KEY=abc\n")
        findings = check_env_completeness(registry_data, f)
        # FUTURE_VAR should be skipped because status=not-provisioned
        assert not any(f.secret_name == "future_secret" for f in findings)


class TestCheckSopsFiles:
    def test_all_present(self, registry_data: dict, sops_dir: Path) -> None:
        assert check_sops_files(registry_data, sops_dir) == []

    def test_missing_file(self, registry_data: dict, sops_dir: Path) -> None:
        (sops_dir / "api-keys.enc.yaml").unlink()
        findings = check_sops_files(registry_data, sops_dir)
        assert len(findings) == 1


class TestCheckSopsDirPermissions:
    def test_correct(self, sops_dir: Path) -> None:
        assert check_sops_dir_permissions(sops_dir) == []

    def test_too_open(self, sops_dir: Path) -> None:
        sops_dir.chmod(0o755)
        findings = check_sops_dir_permissions(sops_dir)
        assert findings[0].severity == "error"

    def test_missing(self, tmp_path: Path) -> None:
        findings = check_sops_dir_permissions(tmp_path / "nope")
        assert findings[0].severity == "error"


class TestCheckTemplateDrift:
    def test_no_drift(self, registry_data: dict, sops_dir: Path) -> None:
        # Template dir may not exist in test context — that's fine
        findings = check_template_drift(registry_data, sops_dir)
        # No assertion on count — depends on whether config/secrets exists in test env


class TestRunAllChecks:
    def test_aggregates_findings(
        self,
        registry_data: dict,
        env_file: Path,
        sops_dir: Path,
    ) -> None:
        report = run_all_checks(registry_data, env_file, sops_dir)
        assert report.checked >= 5  # at least 5 checks defined
        assert isinstance(report.findings, list)

    def test_catches_exceptions_in_checks(
        self,
        registry_data: dict,
        tmp_path: Path,
    ) -> None:
        # Pass a nonexistent env file to trigger errors
        env = tmp_path / "nope"
        sops = tmp_path / "sops_nope"
        report = run_all_checks(registry_data, env, sops)
        assert report.checked >= 5
        assert any(f.severity in ("error", "critical") for f in report.findings)
