"""Shared pytest fixtures for OsMEN-OC test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="1-0")
    redis.xread = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def mock_pg_pool():
    """Mock PostgreSQL connection pool.

    Returns a ``(pool, conn)`` tuple where ``pool.acquire()`` is an async
    context manager that yields ``conn``, and ``conn.transaction()`` is an
    async context manager suitable for use in ``async with`` blocks.
    """
    conn = AsyncMock()

    # conn.transaction() must work as an async context manager
    transaction_ctx = AsyncMock()
    transaction_ctx.__aenter__ = AsyncMock(return_value=None)
    transaction_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=transaction_ctx)

    # pool.acquire() must work as an async context manager yielding conn
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_ctx)

    return pool, conn


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
