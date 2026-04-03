"""Shared pytest fixtures for OsMEN-OC test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="msg-id")
    redis.xread = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def mock_pg_pool():
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    return pool


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
