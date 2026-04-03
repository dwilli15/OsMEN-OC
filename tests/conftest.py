"""Shared pytest fixtures for OsMEN-OC tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="1-0")
    redis.xread = AsyncMock(return_value=[])
    redis.xreadgroup = AsyncMock(return_value=[])
    redis.xack = AsyncMock(return_value=1)
    redis.xgroup_create = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_pg_pool():
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.fetch = AsyncMock(return_value=[])
    conn.transaction = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock(return_value=False)))
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock(return_value=False)))
    return pool, conn


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
