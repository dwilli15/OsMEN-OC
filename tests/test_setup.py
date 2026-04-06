"""Tests for the first-run setup wizard (core/setup/)."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from core.setup.wizard import (
    _ENV_FIELD_MAP,
    SetupConfig,
    SetupWizard,
)
from core.utils.exceptions import OsMENError, SetupError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wizard(
    tmp_path: Path,
    *,
    stdin_text: str = "\n" * 20,
    auto: bool = False,
    reconfigure: bool = False,
) -> tuple[SetupWizard, StringIO]:
    """Return a wizard wired to *tmp_path* with injected stdin/stdout."""
    stdin = StringIO(stdin_text)
    stdout = StringIO()
    wizard = SetupWizard(
        auto=auto,
        reconfigure=reconfigure,
        repo_root=tmp_path,
        stdin=stdin,
        stdout=stdout,
        use_getpass=False,
    )
    # Redirect home-relative paths into tmp_path for test isolation.
    wizard._env_dir = tmp_path / "osmen_cfg"
    wizard._env_file = wizard._env_dir / "env"
    wizard._state_file = wizard._env_dir / ".setup_complete"
    wizard._openclaw_config = tmp_path / "config" / "openclaw.yaml"
    return wizard, stdout


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_setup_error_inherits_osmen_error() -> None:
    assert issubclass(SetupError, OsMENError)


def test_setup_error_carries_correlation_id() -> None:
    exc = SetupError("boom", correlation_id="trace-123")
    assert exc.correlation_id == "trace-123"
    assert str(exc) == "boom"


# ---------------------------------------------------------------------------
# SetupConfig defaults
# ---------------------------------------------------------------------------


def test_setup_config_defaults() -> None:
    cfg = SetupConfig()
    assert cfg.openclaw_ws_url == "ws://127.0.0.1:18789"
    assert cfg.postgres_dsn == "postgresql://osmen:osmen@localhost:5432/osmen"
    assert cfg.redis_url == "redis://localhost:6379"
    assert cfg.zai_api_key == ""
    assert cfg.telegram_bot_token == ""
    assert cfg.discord_bot_token == ""


def test_env_field_map_covers_all_config_fields() -> None:
    """Every SetupConfig field must appear in _ENV_FIELD_MAP."""
    config_fields = set(SetupConfig.model_fields.keys())
    mapped_fields = set(_ENV_FIELD_MAP.values())
    assert config_fields == mapped_fields, (
        f"Missing from _ENV_FIELD_MAP: {config_fields - mapped_fields}"
    )


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


def test_is_configured_false_when_state_absent(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path)
    assert wizard.is_configured() is False


def test_is_configured_true_when_state_present(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path)
    wizard._env_dir.mkdir(parents=True, exist_ok=True)
    wizard._state_file.write_text("configured_at: 2026-01-01T00:00:00+00:00\n")
    assert wizard.is_configured() is True


# ---------------------------------------------------------------------------
# Already-configured short-circuit
# ---------------------------------------------------------------------------


def test_wizard_skips_when_already_configured(tmp_path: Path) -> None:
    wizard, stdout = _make_wizard(tmp_path)
    wizard._env_dir.mkdir(parents=True, exist_ok=True)
    wizard._state_file.write_text("configured_at: 2026-01-01T00:00:00+00:00\n")

    rc = wizard.run()

    assert rc == 0
    assert "already configured" in stdout.getvalue()
    assert not wizard._env_file.exists()


def test_reconfigure_bypasses_state_check(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True, reconfigure=True)
    wizard._env_dir.mkdir(parents=True, exist_ok=True)
    wizard._state_file.write_text("configured_at: 2026-01-01T00:00:00+00:00\n")

    rc = wizard.run()

    assert rc == 0
    assert wizard._env_file.exists()


# ---------------------------------------------------------------------------
# Auto mode — writes env file and openclaw.yaml
# ---------------------------------------------------------------------------


def test_auto_mode_writes_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    wizard, _ = _make_wizard(tmp_path, auto=True)
    rc = wizard.run()

    assert rc == 0
    assert wizard._env_file.exists()
    content = wizard._env_file.read_text()
    assert "ZAI_API_KEY=test-zai-key" in content
    assert "TELEGRAM_BOT_TOKEN=tg-token" in content
    assert "TELEGRAM_CHAT_ID=12345" in content


def test_auto_mode_uses_default_dsns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("POSTGRES_DSN", "REDIS_URL", "OPENCLAW_WS_URL"):
        monkeypatch.delenv(key, raising=False)

    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard.run()

    content = wizard._env_file.read_text()
    assert "POSTGRES_DSN=postgresql://osmen:osmen@localhost:5432/osmen" in content
    assert "REDIS_URL=redis://localhost:6379" in content
    assert "OPENCLAW_WS_URL=ws://127.0.0.1:18789" in content


def test_auto_mode_marks_setup_complete(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    assert not wizard._state_file.exists()

    wizard.run()

    assert wizard._state_file.exists()
    assert "configured_at:" in wizard._state_file.read_text()


def test_auto_mode_writes_openclaw_config(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard.run()

    assert wizard._openclaw_config.exists()
    data = yaml.safe_load(wizard._openclaw_config.read_text())
    assert "bridge" in data
    assert "trust_policy" in data
    assert data["bridge"]["ws_url"] == "ws://127.0.0.1:18789"
    assert data["telegram"]["token"] == "${TELEGRAM_BOT_TOKEN}"
    assert data["discord"]["token"] == "${DISCORD_BOT_TOKEN}"


def test_auto_mode_openclaw_ws_url_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENCLAW_WS_URL", "ws://10.0.0.5:18789")

    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard.run()

    data = yaml.safe_load(wizard._openclaw_config.read_text())
    assert data["bridge"]["ws_url"] == "ws://10.0.0.5:18789"


# ---------------------------------------------------------------------------
# Env file properties
# ---------------------------------------------------------------------------


def test_env_file_permissions(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard.run()

    mode = oct(wizard._env_file.stat().st_mode & 0o777)
    assert mode == oct(0o600), f"Expected 0o600, got {mode}"


def test_env_file_has_header_comment(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard.run()

    first_line = wizard._env_file.read_text().splitlines()[0]
    assert first_line.startswith("#")


# ---------------------------------------------------------------------------
# Interactive prompting
# ---------------------------------------------------------------------------


def test_interactive_prompt_uses_stdin(tmp_path: Path) -> None:
    stdin_text = (
        "my-zai-key\n"  # ZAI API key
        "tg-bot-tok\n"  # Telegram token
        "999888\n"  # Telegram chat ID
        "\n"  # Discord token (skip)
        "\n"  # ws_url (default)
        "\n"  # plex (default)
        "\n"  # staging (default)
        "\n"  # postgres DSN (default)
        "\n"  # Redis URL (default)
    )
    wizard, _ = _make_wizard(tmp_path, stdin_text=stdin_text)
    rc = wizard.run()

    assert rc == 0
    content = wizard._env_file.read_text()
    assert "ZAI_API_KEY=my-zai-key" in content
    assert "TELEGRAM_BOT_TOKEN=tg-bot-tok" in content
    assert "TELEGRAM_CHAT_ID=999888" in content


def test_interactive_default_accepted_on_empty_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Provide required fields via env; press Enter for everything else (accepts defaults).
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    wizard, _ = _make_wizard(tmp_path, stdin_text="\n" * 20)
    wizard.run()

    content = wizard._env_file.read_text()
    assert "POSTGRES_DSN=postgresql://osmen:osmen@localhost:5432/osmen" in content


def test_interactive_env_var_prefills_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ZAI_API_KEY", "env-prefilled-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    wizard, _ = _make_wizard(tmp_path, stdin_text="\n" * 20)
    wizard.run()

    content = wizard._env_file.read_text()
    assert "ZAI_API_KEY=env-prefilled-key" in content


# ---------------------------------------------------------------------------
# Load existing env file (reconfigure)
# ---------------------------------------------------------------------------


def test_load_existing_env_populates_config(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard._env_dir.mkdir(parents=True, exist_ok=True)
    wizard._env_file.write_text("ZAI_API_KEY=existing-key\nTELEGRAM_BOT_TOKEN=existing-tg\n")
    wizard._env_file.chmod(0o600)

    wizard._load_existing_env()

    assert wizard._config.zai_api_key == "existing-key"
    assert wizard._config.telegram_bot_token == "existing-tg"


def test_load_existing_env_ignores_comments(tmp_path: Path) -> None:
    wizard, _ = _make_wizard(tmp_path, auto=True)
    wizard._env_dir.mkdir(parents=True, exist_ok=True)
    wizard._env_file.write_text("# This is a comment\n\nZAI_API_KEY=from-file\n")
    wizard._env_file.chmod(0o600)

    wizard._load_existing_env()

    assert wizard._config.zai_api_key == "from-file"


def test_reconfigure_preserves_unedited_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ZAI_API_KEY", "first-run-key")
    w1, _ = _make_wizard(tmp_path, auto=True)
    w1.run()

    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    # Reconfigure in auto mode — previously saved values are loaded from env file.
    w2, _ = _make_wizard(tmp_path, auto=True, reconfigure=True)
    w2.run()

    content = w2._env_file.read_text()
    assert "ZAI_API_KEY=first-run-key" in content


# ---------------------------------------------------------------------------
# Cancellation / error handling
# ---------------------------------------------------------------------------


def test_keyboard_interrupt_returns_1(tmp_path: Path) -> None:
    class _InterruptStream:
        def readline(self) -> str:
            raise KeyboardInterrupt

    wizard = SetupWizard(
        repo_root=tmp_path,
        stdin=_InterruptStream(),  # type: ignore[arg-type]
        stdout=StringIO(),
        use_getpass=False,
    )
    wizard._env_dir = tmp_path / "osmen_cfg"
    wizard._env_file = wizard._env_dir / "env"
    wizard._state_file = wizard._env_dir / ".setup_complete"
    wizard._openclaw_config = tmp_path / "config" / "openclaw.yaml"

    assert wizard.run() == 1


def test_eof_error_returns_1(tmp_path: Path) -> None:
    class _EOFStream:
        def readline(self) -> str:
            raise EOFError

    wizard = SetupWizard(
        repo_root=tmp_path,
        stdin=_EOFStream(),  # type: ignore[arg-type]
        stdout=StringIO(),
        use_getpass=False,
    )
    wizard._env_dir = tmp_path / "osmen_cfg"
    wizard._env_file = wizard._env_dir / "env"
    wizard._state_file = wizard._env_dir / ".setup_complete"
    wizard._openclaw_config = tmp_path / "config" / "openclaw.yaml"

    assert wizard.run() == 1


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def test_summary_contains_next_steps(tmp_path: Path) -> None:
    wizard, stdout = _make_wizard(tmp_path, auto=True)
    wizard.run()

    output = stdout.getvalue()
    assert "source" in output
    assert "make up" in output
    assert "openclaw start" in output


# ---------------------------------------------------------------------------
# __main__ entry point
# ---------------------------------------------------------------------------


def test_main_help_exits_0() -> None:
    from core.setup.__main__ import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_main_auto_flag_passed() -> None:
    from core.setup.__main__ import main

    with patch("core.setup.__main__.run_wizard", return_value=0) as mock_run:
        rc = main(["--auto"])
    assert rc == 0
    mock_run.assert_called_once_with(auto=True, reconfigure=False)


def test_main_reconfigure_flag_passed() -> None:
    from core.setup.__main__ import main

    with patch("core.setup.__main__.run_wizard", return_value=0) as mock_run:
        rc = main(["--reconfigure"])
    assert rc == 0
    mock_run.assert_called_once_with(auto=False, reconfigure=True)
