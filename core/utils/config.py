"""YAML configuration loader with ``${ENV_VAR}`` interpolation.

Usage::

    from core.utils.config import load_config

    config = load_config("config/llm/providers.yaml")
    # ${ZAI_API_KEY} is automatically resolved from the environment.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from core.utils.exceptions import ConfigError

_ENV_RE = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value: Any) -> Any:
    """Recursively resolve ``${ENV_VAR}`` placeholders in *value*.

    Args:
        value: A string, dict, list, or scalar loaded from YAML.

    Returns:
        The value with all ``${ENV_VAR}`` references replaced by the
        corresponding environment-variable values.

    Raises:
        ConfigError: If a referenced environment variable is not set.
    """
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            var = match.group(1)
            env_val = os.environ.get(var)
            if env_val is None:
                raise ConfigError(f"Environment variable '{var}' is not set")
            return env_val

        return _ENV_RE.sub(_replace, value)

    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_interpolate(item) for item in value]

    return value


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file and resolve ``${ENV_VAR}`` placeholders.

    Args:
        path: Path to the YAML config file (absolute or relative to CWD).

    Returns:
        Fully-interpolated configuration dictionary.

    Raises:
        ConfigError: If the file does not exist or a variable is missing.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    logger.debug("Loading config from {}", config_path)

    with config_path.open() as fh:
        raw: Any = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must contain a YAML mapping: {config_path}")

    return _interpolate(raw)
