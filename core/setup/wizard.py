"""Semi-automated interactive first-run setup wizard for OsMEN-OC.

Gathers required configuration values from the operator (or from environment
variables in ``--auto`` mode) and writes them to:

* ``~/.config/osmen/env``   — shell-sourceable env file (chmod 0o600, not committed)
* ``config/openclaw.yaml``  — OpenClaw bridge config template (env-var placeholders)

A state file at ``~/.config/osmen/.setup_complete`` prevents the wizard from
re-running on every bootstrap unless ``--reconfigure`` is passed.
"""

from __future__ import annotations

import getpass as _getpass
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

import yaml
from loguru import logger
from pydantic import BaseModel

from core.utils.exceptions import SetupError


class SetupConfig(BaseModel):
    """All configuration gathered during the first-run setup wizard."""

    # LLM / GLM API (Zhipu AI)
    zai_api_key: str = ""

    # OpenClaw control-plane
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_bot_token: str = ""  # optional
    discord_guild_id: str = ""  # optional
    openclaw_ws_url: str = "ws://127.0.0.1:18789"

    # Media directories
    plex_library_root: str = ""
    download_staging_dir: str = ""

    # Core service DSNs
    postgres_dsn: str = "postgresql://osmen:osmen@localhost:5432/osmen"
    redis_url: str = "redis://localhost:6379"


# Map of env-var name → SetupConfig field name.
_ENV_FIELD_MAP: dict[str, str] = {
    "ZAI_API_KEY": "zai_api_key",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "TELEGRAM_CHAT_ID": "telegram_chat_id",
    "DISCORD_BOT_TOKEN": "discord_bot_token",
    "DISCORD_GUILD_ID": "discord_guild_id",
    "OPENCLAW_WS_URL": "openclaw_ws_url",
    "PLEX_LIBRARY_ROOT": "plex_library_root",
    "DOWNLOAD_STAGING_DIR": "download_staging_dir",
    "POSTGRES_DSN": "postgres_dsn",
    "REDIS_URL": "redis_url",
}


class SetupWizard:
    """Semi-automated interactive first-run configuration wizard.

    Args:
        auto: Skip all prompts; use environment variables and defaults.
        reconfigure: Re-run even if setup is already marked complete.
        repo_root: Path to the repository root (auto-detected if omitted).
        stdin: Input stream (defaults to ``sys.stdin``).
        stdout: Output stream (defaults to ``sys.stdout``).
        use_getpass: Whether to hide secret input (set ``False`` in tests).
    """

    def __init__(
        self,
        *,
        auto: bool = False,
        reconfigure: bool = False,
        repo_root: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        use_getpass: bool = True,
    ) -> None:
        self.auto = auto
        self.reconfigure = reconfigure
        self._in: IO[str] = stdin if stdin is not None else sys.stdin
        self._out: IO[str] = stdout if stdout is not None else sys.stdout
        self._use_getpass = use_getpass
        self._config = SetupConfig()

        # wizard.py lives at core/setup/wizard.py → repo root is two levels up.
        self._repo_root: Path = repo_root if repo_root is not None else Path(__file__).parents[2]

        self._env_dir: Path = Path.home() / ".config" / "osmen"
        self._env_file: Path = self._env_dir / "env"
        self._state_file: Path = self._env_dir / ".setup_complete"
        self._openclaw_config: Path = self._repo_root / "config" / "openclaw.yaml"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return ``True`` if first-run setup has already been completed."""
        return self._state_file.exists()

    def run(self) -> int:
        """Execute the setup wizard.

        Returns:
            0 on success, 1 on cancellation or error.
        """
        try:
            return self._run()
        except (KeyboardInterrupt, EOFError):
            self._println("\n\n  Setup cancelled.")
            return 1
        except SetupError as exc:
            logger.error("Setup failed: {}", exc)
            return 1

    # ------------------------------------------------------------------
    # Internal flow
    # ------------------------------------------------------------------

    def _run(self) -> int:
        if self.is_configured() and not self.reconfigure:
            self._println(
                "✓ OsMEN-OC is already configured.\n"
                "  Run with --reconfigure to update settings."
            )
            return 0

        self._print_banner()
        self._load_existing_env()

        self._section("LLM / GLM API")
        self._gather_llm_config()

        self._section("OpenClaw Control Plane")
        self._gather_openclaw_config()

        self._section("Media Directories")
        self._gather_media_config()

        self._section("Core Service Endpoints")
        self._gather_service_config()

        self._section("Writing Configuration")
        self._write_env_file()
        self._write_openclaw_config()
        self._mark_complete()

        self._print_summary()
        return 0

    # ------------------------------------------------------------------
    # Configuration gathering
    # ------------------------------------------------------------------

    def _gather_llm_config(self) -> None:
        self._println(
            "  The ZAI API key authenticates cloud-primary LLM requests (Zhipu GLM).\n"
            "  Get yours at: https://open.bigmodel.cn/usercenter/apikeys\n"
        )
        self._config.zai_api_key = self._prompt_secret(
            "  ZAI API key",
            env_var="ZAI_API_KEY",
            current=self._config.zai_api_key,
        )

    def _gather_openclaw_config(self) -> None:
        self._println(
            "  OpenClaw routes Telegram/Discord messages to this execution engine.\n"
            "  A Telegram bot is required for medium/high/critical approval notifications.\n"
        )
        self._config.telegram_bot_token = self._prompt_secret(
            "  Telegram bot token",
            env_var="TELEGRAM_BOT_TOKEN",
            current=self._config.telegram_bot_token,
        )
        self._config.telegram_chat_id = self._prompt(
            "  Telegram chat ID",
            env_var="TELEGRAM_CHAT_ID",
            current=self._config.telegram_chat_id,
        )

        self._println("\n  Discord integration is optional — press Enter to skip.\n")
        self._config.discord_bot_token = self._prompt_secret(
            "  Discord bot token (optional)",
            env_var="DISCORD_BOT_TOKEN",
            current=self._config.discord_bot_token,
            required=False,
        )
        if self._config.discord_bot_token:
            self._config.discord_guild_id = self._prompt(
                "  Discord guild/server ID",
                env_var="DISCORD_GUILD_ID",
                current=self._config.discord_guild_id,
                required=False,
            )

        self._config.openclaw_ws_url = self._prompt(
            "  OpenClaw WebSocket URL",
            env_var="OPENCLAW_WS_URL",
            current=self._config.openclaw_ws_url,
            default=SetupConfig.model_fields["openclaw_ws_url"].default,  # type: ignore[arg-type]
        )

    def _gather_media_config(self) -> None:
        self._println(
            "  Set paths for Plex library storage and download staging.\n"
            "  Leave blank to skip (media features will be unavailable).\n"
        )
        default_plex = str(Path.home() / "media")
        default_staging = str(Path.home() / "downloads")

        self._config.plex_library_root = self._prompt(
            "  Plex library root",
            env_var="PLEX_LIBRARY_ROOT",
            current=self._config.plex_library_root,
            default=default_plex,
            required=False,
        )
        self._config.download_staging_dir = self._prompt(
            "  Download staging directory",
            env_var="DOWNLOAD_STAGING_DIR",
            current=self._config.download_staging_dir,
            default=default_staging,
            required=False,
        )

    def _gather_service_config(self) -> None:
        self._println(
            "  Accept the defaults unless you have customised the Podman service configuration.\n"
        )
        self._config.postgres_dsn = self._prompt(
            "  PostgreSQL DSN",
            env_var="POSTGRES_DSN",
            current=self._config.postgres_dsn,
            default=SetupConfig.model_fields["postgres_dsn"].default,  # type: ignore[arg-type]
        )
        self._config.redis_url = self._prompt(
            "  Redis URL",
            env_var="REDIS_URL",
            current=self._config.redis_url,
            default=SetupConfig.model_fields["redis_url"].default,  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------
    # Output writers
    # ------------------------------------------------------------------

    def _write_env_file(self) -> None:
        """Write ``~/.config/osmen/env`` with all configured values."""
        self._env_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).isoformat(timespec="seconds")
        lines: list[str] = [
            "# OsMEN-OC environment configuration",
            f"# Generated by: python -m core.setup  ({timestamp})",
            "# Source this file before starting services:",
            "#   source ~/.config/osmen/env",
            "# Do NOT commit this file — it contains secrets.",
            "",
            "# LLM / GLM API",
            f"ZAI_API_KEY={self._config.zai_api_key}",
            "",
            "# OpenClaw control-plane",
            f"TELEGRAM_BOT_TOKEN={self._config.telegram_bot_token}",
            f"TELEGRAM_CHAT_ID={self._config.telegram_chat_id}",
            f"DISCORD_BOT_TOKEN={self._config.discord_bot_token}",
            f"DISCORD_GUILD_ID={self._config.discord_guild_id}",
            f"OPENCLAW_WS_URL={self._config.openclaw_ws_url}",
            "",
            "# Media directories",
            f"PLEX_LIBRARY_ROOT={self._config.plex_library_root}",
            f"DOWNLOAD_STAGING_DIR={self._config.download_staging_dir}",
            "",
            "# Core service endpoints",
            f"POSTGRES_DSN={self._config.postgres_dsn}",
            f"REDIS_URL={self._config.redis_url}",
        ]
        self._env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._env_file.chmod(0o600)
        self._println(f"  ✓ Wrote {self._env_file}")

    def _write_openclaw_config(self) -> None:
        """Write ``config/openclaw.yaml`` with env-var placeholders.

        The file is safe to commit — it contains ``${ENV_VAR}`` references, not
        real secrets.  The actual values live in ``~/.config/osmen/env``.
        """
        config_data: dict[str, Any] = {
            "bridge": {
                "ws_url": self._config.openclaw_ws_url,
                "reconnect_interval_seconds": 5,
                "max_message_bytes": 65536,
            },
            "telegram": {
                "token": "${TELEGRAM_BOT_TOKEN}",
                "chat_id": "${TELEGRAM_CHAT_ID}",
                "parse_mode": "MarkdownV2",
            },
            "discord": {
                "token": "${DISCORD_BOT_TOKEN}",
                "guild_id": "${DISCORD_GUILD_ID}",
            },
            "trust_policy": {
                "allowed_channels": ["telegram", "discord"],
                "require_approval_risk_levels": ["high", "critical"],
            },
        }
        self._openclaw_config.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "# OpenClaw control-plane bridge configuration\n"
            "# Generated by: python -m core.setup\n"
            "# ${ENV_VAR} references are resolved from ~/.config/osmen/env — safe to commit.\n\n"
        )
        with open(self._openclaw_config, "w", encoding="utf-8") as fh:
            fh.write(header)
            yaml.dump(
                config_data,
                fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        self._println(f"  ✓ Wrote {self._openclaw_config}")

    def _mark_complete(self) -> None:
        """Create the state file that prevents the wizard from re-running."""
        timestamp = datetime.now(tz=UTC).isoformat(timespec="seconds")
        self._state_file.write_text(f"configured_at: {timestamp}\n", encoding="utf-8")
        self._println(f"  ✓ Marked setup complete ({self._state_file})")

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        self._println(
            "\n╔══════════════════════════════════════════════════╗\n"
            "║          OsMEN-OC First Run Setup                ║\n"
            "║  Semi-automated interactive configuration wizard ║\n"
            "╚══════════════════════════════════════════════════╝\n"
        )
        if self.auto:
            self._println("  Running in auto mode — prompts use env vars or defaults.\n")
        else:
            self._println(
                "  Press Enter to accept the default shown in [brackets].\n"
                "  Values already in your environment are pre-filled.\n"
            )

    def _print_summary(self) -> None:
        self._println(
            "\n╔══════════════════════════════════════════════════╗\n"
            "║              Setup Complete ✓                   ║\n"
            "╚══════════════════════════════════════════════════╝\n"
        )
        self._println("  Next steps:")
        self._println(f"    source {self._env_file}")
        self._println("    make up          # start core services")
        self._println("    make dev         # start the gateway API")
        self._println("    openclaw start   # start the control plane")
        self._println()

    def _section(self, title: str) -> None:
        fill = "─" * max(0, 44 - len(title))
        self._println(f"\n── {title} {fill}")

    def _println(self, msg: str = "") -> None:
        print(msg, file=self._out)

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------

    def _load_existing_env(self) -> None:
        """Pre-populate config from an existing env file when reconfiguring."""
        if not self._env_file.exists():
            return
        raw = self._env_file.read_text(encoding="utf-8")
        env_map: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, val = stripped.partition("=")
                env_map[key.strip()] = val.strip()
        for env_key, field_name in _ENV_FIELD_MAP.items():
            if env_map.get(env_key):
                setattr(self._config, field_name, env_map[env_key])

    def _prompt(
        self,
        label: str,
        *,
        env_var: str | None = None,
        current: str = "",
        default: str = "",
        required: bool = True,
    ) -> str:
        """Prompt for a plain-text value.

        Resolution order (first non-empty wins): env var → *current* → *default*.
        In auto mode returns the resolved value without prompting.
        """
        env_value = os.environ.get(env_var, "") if env_var else ""
        resolved = env_value or current or default

        if self.auto:
            return resolved

        display = f"[{resolved}] " if resolved else ""
        self._out.write(f"{label}: {display}")
        self._out.flush()
        entered = self._in.readline().rstrip("\n")
        value = entered if entered else resolved

        while required and not value:
            self._out.write(f"  ✗ Required — {label}: ")
            self._out.flush()
            entered = self._in.readline().rstrip("\n")
            value = entered

        return value

    def _prompt_secret(
        self,
        label: str,
        *,
        env_var: str | None = None,
        current: str = "",
        required: bool = True,
    ) -> str:
        """Prompt for a secret value (input hidden in interactive mode).

        If a value already exists (from env var or *current*), pressing Enter
        keeps the existing value.  Env var takes precedence over *current*.
        """
        env_value = os.environ.get(env_var, "") if env_var else ""
        resolved = env_value or current

        if self.auto:
            return resolved

        hint = " [keep existing]" if resolved else ""
        prompt_str = f"{label}{hint}: "

        entered = self._read_secret(prompt_str)
        value = entered if entered else resolved

        while required and not value:
            entered = self._read_secret(f"  ✗ Required — {label}: ")
            value = entered if entered else resolved

        return value

    def _read_secret(self, prompt_str: str) -> str:
        """Read a single secret line, optionally hiding echo."""
        if self._use_getpass:
            return _getpass.getpass(prompt_str, stream=self._out)
        self._out.write(prompt_str)
        self._out.flush()
        return self._in.readline().rstrip("\n")


def run_wizard(
    *,
    auto: bool = False,
    reconfigure: bool = False,
    repo_root: Path | None = None,
) -> int:
    """Run the setup wizard and return an exit code (0 = success, 1 = error).

    Args:
        auto: Skip all interactive prompts; use env vars / defaults.
        reconfigure: Re-run even if setup is already marked complete.
        repo_root: Override repository root path (for testing).
    """
    wizard = SetupWizard(auto=auto, reconfigure=reconfigure, repo_root=repo_root)
    return wizard.run()
