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

from core.utils.exceptions import ConfigError

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_config_path(path: str | Path, allowed_roots: list[str | Path] | None = None) -> Path:
    candidate = Path(path).expanduser()
    resolved = candidate if candidate.is_absolute() else (_REPO_ROOT / candidate)
    resolved = resolved.resolve()

    trusted_roots = allowed_roots if allowed_roots is not None else [_REPO_ROOT / "config"]
    normalized_roots = [Path(root).expanduser().resolve() for root in trusted_roots]
    if not any(_is_within(resolved, root) for root in normalized_roots):
        allowed_text = ", ".join(str(root) for root in normalized_roots)
        raise ConfigError(f"Config path not allowed: {resolved}. Allowed roots: {allowed_text}")

    return resolved


def _interpolate(value: Any) -> Any:
    """Recursively resolve ``${ENV_VAR}`` tokens in string values."""
    if isinstance(value, str):

        def _replace(match: re.Match[str]) -> str:
            var = match.group(1)
            resolved = os.environ.get(var)
            if resolved is None:
                raise ConfigError(f"Config references undefined env var: {var}")
            return resolved

        return _ENV_PATTERN.sub(_replace, value)

    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_interpolate(item) for item in value]

    return value


def load_config(
    path: str | Path,
    *,
    allowed_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Load a YAML config file, resolving ``${ENV_VAR}`` placeholders.

    Args:
        path: Path to the YAML file (relative or absolute).
        allowed_roots: Optional trusted root directories. If omitted,
            only ``<repo>/config`` is allowed.

    Returns:
        Parsed and interpolated configuration dictionary.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    resolved = _resolve_config_path(path, allowed_roots)

    try:
        raw = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Config file not found: {resolved}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in {resolved}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file {resolved} must contain a YAML mapping, got {type(data).__name__}"
        )

    return _interpolate(data)
