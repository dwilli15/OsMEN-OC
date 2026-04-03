"""YAML configuration loader with ``${ENV_VAR}`` interpolation.

Usage::

    from core.utils.config import load_config

    config = load_config("config/agents.yaml")
    # ${MY_VAR} placeholders are resolved from the environment.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from core.utils.exceptions import ConfigError

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value: Any) -> Any:
    """Recursively resolve ``${ENV_VAR}`` tokens in string values."""
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            var = match.group(1)
            resolved = os.environ.get(var)
            if resolved is None:
                logger.warning("Config references undefined env var: {}", var)
                return match.group(0)
            return resolved

        return _ENV_PATTERN.sub(_replace, value)

    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_interpolate(item) for item in value]

    return value


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file, resolving ``${ENV_VAR}`` placeholders.

    Args:
        path: Path to the YAML file (relative or absolute).

    Returns:
        Parsed and interpolated configuration dictionary.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    try:
        raw = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {resolved}: {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in {resolved}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Expected a YAML mapping in {resolved}, got {type(data).__name__}")

    return _interpolate(data)
