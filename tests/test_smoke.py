"""Smoke tests to verify project scaffolding is in place."""
from __future__ import annotations

import importlib

import pytest


def test_core_package_importable():
    """The core package must be importable."""
    mod = importlib.import_module("core")
    assert mod is not None


@pytest.mark.anyio
async def test_mock_redis_fixture(mock_redis):
    """Redis mock fixture must support xadd and xread."""
    msg_id = await mock_redis.xadd("events:test:ping", {"data": "hello"})
    assert msg_id == "1-0"

    result = await mock_redis.xread({"events:test:ping": "0"})
    assert result == []


@pytest.mark.anyio
async def test_mock_pg_pool_fixture(mock_pg_pool):
    """PostgreSQL mock pool fixture must expose an async-context-manager acquire."""
    pool, conn = mock_pg_pool
    async with pool.acquire() as c:
        assert c is conn


@pytest.mark.anyio
async def test_mock_chromadb_fixture(mock_chromadb):
    """ChromaDB mock fixture must support get_or_create_collection."""
    await mock_chromadb.get_or_create_collection("test-collection")
    mock_chromadb.get_or_create_collection.assert_awaited_once_with("test-collection")
