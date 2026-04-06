"""Tests for core.audit.trail."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from core.audit.trail import DEFAULT_RETENTION_DAYS, AuditRecord, AuditTrail
from core.utils.exceptions import AuditError


def _make_record(**kwargs) -> AuditRecord:
    defaults: dict[str, Any] = {
        "agent_id": "test_agent",
        "tool_name": "test_tool",
        "risk_level": "low",
        "outcome": "approved",
        "reason": "auto-approved",
        "parameters": {"key": "value"},
    }
    defaults.update(kwargs)
    return AuditRecord(**defaults)


# ---------------------------------------------------------------------------
# AuditRecord dataclass
# ---------------------------------------------------------------------------


def test_audit_record_defaults():
    """AuditRecord auto-populates record_id and created_at."""
    record = _make_record()
    assert record.record_id  # non-empty UUID string
    assert record.created_at.tzinfo is not None
    assert record.flagged_for_summary is False


def test_audit_record_custom_fields():
    """AuditRecord stores all provided fields."""
    record = _make_record(
        agent_id="media_steward",
        tool_name="transfer_file",
        risk_level="medium",
        outcome="approved",
        reason="human approved",
        parameters={"src": "/tmp/a", "dst": "/mnt/b"},
        correlation_id="corr-xyz",
        flagged_for_summary=True,
    )
    assert record.agent_id == "media_steward"
    assert record.tool_name == "transfer_file"
    assert record.correlation_id == "corr-xyz"
    assert record.flagged_for_summary is True


# ---------------------------------------------------------------------------
# AuditTrail.insert
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_audit_trail_insert(mock_pg_pool):
    """insert() executes the correct SQL and returns the record_id."""
    pool, conn = mock_pg_pool
    trail = AuditTrail(pool)
    record = _make_record()
    returned_id = await trail.insert(record)

    assert returned_id == record.record_id
    conn.execute.assert_called_once()
    # Verify the first positional SQL arg contains the expected table name
    sql_arg = conn.execute.call_args[0][0]
    assert "audit_trail" in sql_arg


@pytest.mark.anyio
async def test_audit_trail_insert_raises_on_db_error(mock_pg_pool):
    """insert() wraps database errors in AuditError."""
    pool, conn = mock_pg_pool
    conn.execute = AsyncMock(side_effect=RuntimeError("db down"))
    trail = AuditTrail(pool)
    with pytest.raises(AuditError):
        await trail.insert(_make_record())


# ---------------------------------------------------------------------------
# AuditTrail.query
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_audit_trail_query_no_filters(mock_pg_pool):
    """query() with no filters returns results from the database."""
    import json

    pool, conn = mock_pg_pool
    now = datetime.now(UTC)
    fake_row = {
        "record_id": "rec-1",
        "agent_id": "test_agent",
        "tool_name": "test_tool",
        "risk_level": "low",
        "outcome": "approved",
        "reason": "auto-approved",
        "parameters": json.dumps({"key": "value"}),
        "correlation_id": None,
        "flagged_for_summary": False,
        "created_at": now,
    }
    conn.fetch = AsyncMock(return_value=[fake_row])
    trail = AuditTrail(pool)
    results = await trail.query()

    assert len(results) == 1
    assert results[0].record_id == "rec-1"
    assert results[0].agent_id == "test_agent"


@pytest.mark.anyio
async def test_audit_trail_query_empty_result(mock_pg_pool):
    """query() returns an empty list when the database has no matching rows."""
    pool, conn = mock_pg_pool
    conn.fetch = AsyncMock(return_value=[])
    trail = AuditTrail(pool)
    results = await trail.query(agent_id="nobody")
    assert results == []


@pytest.mark.anyio
async def test_audit_trail_query_raises_on_db_error(mock_pg_pool):
    """query() wraps database errors in AuditError."""
    pool, conn = mock_pg_pool
    conn.fetch = AsyncMock(side_effect=RuntimeError("connection lost"))
    trail = AuditTrail(pool)
    with pytest.raises(AuditError):
        await trail.query()


# ---------------------------------------------------------------------------
# AuditTrail.archive
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_audit_trail_archive(mock_pg_pool):
    """archive() runs insert+delete in a transaction and returns count."""
    pool, conn = mock_pg_pool
    conn.execute = AsyncMock(side_effect=["INSERT 0 3", "DELETE 3"])
    trail = AuditTrail(pool)
    archived = await trail.archive(older_than_days=30)
    assert archived == 3
    # Two execute calls: INSERT INTO archive + DELETE FROM trail
    assert conn.execute.call_count == 2


@pytest.mark.anyio
async def test_audit_trail_archive_default_retention(mock_pg_pool):
    """archive() uses the configured retention_days by default."""
    pool, conn = mock_pg_pool
    conn.execute = AsyncMock(side_effect=["INSERT 0 0", "DELETE 0"])
    trail = AuditTrail(pool, retention_days=7)
    await trail.archive()
    assert conn.execute.call_count == 2


@pytest.mark.anyio
async def test_audit_trail_archive_raises_on_db_error(mock_pg_pool):
    """archive() wraps database errors in AuditError."""
    pool, conn = mock_pg_pool
    conn.execute = AsyncMock(side_effect=RuntimeError("transaction failed"))
    trail = AuditTrail(pool)
    with pytest.raises(AuditError):
        await trail.archive()


def test_default_retention_days():
    """DEFAULT_RETENTION_DAYS is set to 30."""
    assert DEFAULT_RETENTION_DAYS == 30
