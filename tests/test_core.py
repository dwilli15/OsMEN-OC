"""Smoke tests for the core package scaffold."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import core
from core.utils.config import load_config
from core.utils.exceptions import ConfigError, OsMENError

# ---------------------------------------------------------------------------
# Package identity
# ---------------------------------------------------------------------------


def test_core_importable() -> None:
    """``import core`` must succeed and expose __version__."""
    assert core.__name__ == "core"
    assert hasattr(core, "__version__")
    assert isinstance(core.__version__, str)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    """All custom exceptions must inherit from OsMENError."""
    assert issubclass(ConfigError, OsMENError)
    assert issubclass(OsMENError, Exception)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def test_load_config_missing_file() -> None:
    """load_config raises ConfigError for non-existent files."""
    with pytest.raises(ConfigError, match="not found"):
        load_config("/tmp/does_not_exist_osmen.yaml")


def test_load_config_basic(tmp_path: Path) -> None:
    """load_config returns a dict for a plain YAML file."""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text("key: value\nnested:\n  inner: 42\n")
    result = load_config(cfg_file)
    assert result == {"key": "value", "nested": {"inner": 42}}


def test_load_config_env_interpolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """load_config resolves ${ENV_VAR} placeholders from the environment."""
    monkeypatch.setenv("TEST_TOKEN", "secret123")
    cfg_file = tmp_path / "env.yaml"
    cfg_file.write_text("token: ${TEST_TOKEN}\n")
    result = load_config(cfg_file)
    assert result["token"] == "secret123"


def test_load_config_missing_env_var(tmp_path: Path) -> None:
    """load_config raises ConfigError when a referenced env var is absent."""
    cfg_file = tmp_path / "missing.yaml"
    cfg_file.write_text("token: ${OSMEN_MISSING_VAR_XYZ}\n")
    # Make sure the variable is not accidentally set
    os.environ.pop("OSMEN_MISSING_VAR_XYZ", None)
    with pytest.raises(ConfigError, match="OSMEN_MISSING_VAR_XYZ"):
        load_config(cfg_file)


def test_load_config_not_a_mapping(tmp_path: Path) -> None:
    """load_config raises ConfigError when the YAML root is not a dict."""
    cfg_file = tmp_path / "list.yaml"
    cfg_file.write_text("- item1\n- item2\n")
    with pytest.raises(ConfigError, match="must contain a YAML mapping"):
        load_config(cfg_file)


# ---------------------------------------------------------------------------
# Shared fixtures smoke test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_mock_redis_fixture(mock_redis: AsyncMock) -> None:
    """mock_redis fixture provides an AsyncMock with xadd/xread."""
    result = await mock_redis.xadd("stream", {"key": "val"})
    assert result == "1-0"
    result = await mock_redis.xread(streams={"stream": "$"})
    assert result == []


@pytest.mark.anyio
async def test_mock_pg_pool_fixture(mock_pg_pool) -> None:
    """mock_pg_pool fixture provides a (pool, conn) tuple with async acquire."""
    pool, conn = mock_pg_pool
    async with pool.acquire() as c:
        assert c is conn


@pytest.mark.anyio
async def test_mock_chromadb_fixture(mock_chromadb: AsyncMock) -> None:
    """mock_chromadb fixture provides an AsyncMock with get_or_create_collection."""
    await mock_chromadb.get_or_create_collection("test_col")
    mock_chromadb.get_or_create_collection.assert_called_once_with("test_col")
