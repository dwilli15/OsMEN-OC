"""Shared pytest fixtures for OsMEN-OC test suite."""

from __future__ import annotations

from contextlib import asynccontextmanager
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

    Returns:
        Tuple of ``(pool, conn)`` where *pool* is a mock whose ``acquire()``
        is an async context manager that yields *conn*, and *conn* is an
        ``AsyncMock`` with ``execute``, ``fetch``, and ``transaction``
        pre-configured so that :class:`~core.audit.trail.AuditTrail` works
        without a real database.
    """
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])

    @asynccontextmanager
    async def _transaction():
        yield conn

    conn.transaction = _transaction

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire

    return pool, conn


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
