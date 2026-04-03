"""Shared pytest fixtures for OsMEN-OC tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client for unit tests."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="msg-id")
    redis.xread = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def mock_pg_pool() -> AsyncMock:
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    return pool


@pytest.fixture
def mock_chromadb() -> AsyncMock:
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
