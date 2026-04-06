"""Tests for systemd timer and service unit files.

Validates that all units in timers/ use install targets appropriate for
rootless user-level systemd deployment (no system-level targets).

Also validates that scripts/deploy_timers.sh uses --user consistently when
invoking systemd-analyze and systemctl.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TIMERS_DIR = REPO_ROOT / "timers"
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy_timers.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_unit(path: Path) -> configparser.RawConfigParser:
    """Parse a systemd unit file with configparser (ignoring duplicate keys)."""
    parser = configparser.RawConfigParser(strict=False)
    # systemd unit files use '=' as delimiter without spaces around it.
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def _unit_files(suffix: str) -> list[Path]:
    return sorted(TIMERS_DIR.glob(f"*{suffix}"))


# ---------------------------------------------------------------------------
# Parametrised unit-file tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unit_path", _unit_files(".service"), ids=lambda p: p.name)
def test_service_wanted_by_default_target(unit_path: Path) -> None:
    """Service units must declare WantedBy=default.target, not multi-user.target."""
    parser = _parse_unit(unit_path)
    assert parser.has_section("Install"), f"{unit_path.name} must have an [Install] section"
    wanted_by = parser.get("Install", "WantedBy", fallback="")
    # Must contain default.target (user-session target).
    assert "default.target" in wanted_by, (
        f"{unit_path.name}: [Install] WantedBy must include 'default.target', got {wanted_by!r}"
    )
    # Must NOT reference system-only multi-user.target.
    assert "multi-user.target" not in wanted_by, (
        f"{unit_path.name}: [Install] WantedBy must not reference 'multi-user.target' "
        f"(system-level target incompatible with --user session)"
    )


@pytest.mark.parametrize("unit_path", _unit_files(".timer"), ids=lambda p: p.name)
def test_timer_wanted_by_timers_target(unit_path: Path) -> None:
    """Timer units must declare WantedBy=timers.target (valid in user sessions)."""
    parser = _parse_unit(unit_path)
    assert parser.has_section("Install"), f"{unit_path.name} must have an [Install] section"
    wanted_by = parser.get("Install", "WantedBy", fallback="")
    assert "timers.target" in wanted_by, (
        f"{unit_path.name}: [Install] WantedBy must include 'timers.target', got {wanted_by!r}"
    )


@pytest.mark.parametrize("unit_path", _unit_files(".service"), ids=lambda p: p.name)
def test_service_has_unit_section(unit_path: Path) -> None:
    """Service units must have [Unit], [Service], and [Install] sections."""
    parser = _parse_unit(unit_path)
    for section in ("Unit", "Service", "Install"):
        assert parser.has_section(section), f"{unit_path.name} is missing [{section}] section"


@pytest.mark.parametrize("unit_path", _unit_files(".timer"), ids=lambda p: p.name)
def test_timer_has_required_sections(unit_path: Path) -> None:
    """Timer units must have [Unit], [Timer], and [Install] sections."""
    parser = _parse_unit(unit_path)
    for section in ("Unit", "Timer", "Install"):
        assert parser.has_section(section), f"{unit_path.name} is missing [{section}] section"


@pytest.mark.parametrize("unit_path", _unit_files(".service"), ids=lambda p: p.name)
def test_service_type_is_oneshot(unit_path: Path) -> None:
    """Timer-driven service units must declare Type=oneshot."""
    parser = _parse_unit(unit_path)
    svc_type = parser.get("Service", "Type", fallback="")
    assert svc_type.lower() == "oneshot", (
        f"{unit_path.name}: [Service] Type must be 'oneshot', got {svc_type!r}"
    )


# ---------------------------------------------------------------------------
# deploy_timers.sh script validation
# ---------------------------------------------------------------------------


def test_deploy_script_exists() -> None:
    """scripts/deploy_timers.sh must exist."""
    assert DEPLOY_SCRIPT.exists(), f"Missing {DEPLOY_SCRIPT}"


def test_deploy_script_uses_systemctl_user() -> None:
    """deploy_timers.sh must invoke systemctl with --user flag (not as root)."""
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert "systemctl --user" in content, (
        "deploy_timers.sh must use 'systemctl --user' for all systemctl calls"
    )
    # Check that every non-comment line where systemctl is the first executable
    # token (i.e. an actual invocation, not a string argument) includes --user.
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # Only match lines where systemctl starts the command position after
        # stripping leading whitespace. This intentionally targets direct
        # invocations (the only pattern used in this script); invocations
        # after shell conditionals like `&&` are not present in this script.
        if re.match(r"systemctl\b", stripped):
            assert "--user" in stripped, (
                f"deploy_timers.sh: bare systemctl invocation without --user: {line!r}"
            )


def test_deploy_script_uses_systemd_analyze_user() -> None:
    """deploy_timers.sh must invoke systemd-analyze verify with --user flag."""
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    # Script may not have systemd-analyze at all (optional), but if it does,
    # it must use --user.
    if "systemd-analyze" not in content:
        pytest.skip("deploy_timers.sh does not call systemd-analyze")
    assert "systemd-analyze verify --user" in content, (
        "deploy_timers.sh must use 'systemd-analyze verify --user' (not bare verify)"
    )


def test_deploy_script_dry_run_validates_source() -> None:
    """deploy_timers.sh must validate source unit files in --dry-run mode."""
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    # Positive check: the script must assign verify_target to the source
    # unit_file variable (used in dry-run mode before symlinks exist).
    assert 'verify_target="${unit_file}"' in content, (
        "deploy_timers.sh must set verify_target to the source unit_file in "
        "dry-run mode so systemd-analyze runs against the source directly"
    )
    # And must also have a live-mode path that uses the deployed link target.
    assert 'verify_target="${link_target}"' in content, (
        "deploy_timers.sh must set verify_target to link_target in live mode"
    )


def test_deploy_script_is_idempotent_guard() -> None:
    """deploy_timers.sh must use 'ln -sf' (force) for idempotent symlinking."""
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert "ln -sf" in content, (
        "deploy_timers.sh must use 'ln -sf' for atomic, idempotent symlink creation"
    )


def test_deploy_script_deploys_to_user_dir() -> None:
    """deploy_timers.sh must target ~/.config/systemd/user/ (not system paths)."""
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert ".config/systemd/user" in content, (
        "deploy_timers.sh must deploy to ~/.config/systemd/user/"
    )
    # Must not deploy to system unit directories.
    for system_path in ("/etc/systemd/system", "/lib/systemd/system", "/usr/lib/systemd/system"):
        assert system_path not in content, (
            f"deploy_timers.sh must not reference system unit dir {system_path!r}"
        )
