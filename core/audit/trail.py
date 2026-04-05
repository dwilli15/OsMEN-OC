"""Append-only audit trail with query and archive interfaces.

Records every tool invocation outcome (approval gate result) to
PostgreSQL for compliance and post-incident analysis.  Records older
than the configured retention period are moved to a compressed archive
table rather than deleted.

Usage::

    trail = AuditTrail(pg_pool)
    record_id = await trail.insert(result)
    records = await trail.query(agent_id="media_steward", limit=50)
    archived = await trail.archive(older_than_days=30)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from loguru import logger

from core.utils.exceptions import AuditError

if TYPE_CHECKING:
    from asyncpg import Pool

# Default retention period before records are moved to archive
DEFAULT_RETENTION_DAYS = 30


@dataclass
class AuditRecord:
    """A single immutable audit log entry.

    Attributes:
        record_id: UUID primary key for this record.
        agent_id: Agent that requested the tool invocation.
        tool_name: Name of the tool that was invoked (or attempted).
        risk_level: Risk level assessed by the approval gate.
        outcome: Gate decision (``"approved"`` / ``"denied"``).
        reason: Human-readable explanation of the decision.
        parameters: Sanitised snapshot of the tool parameters.
        correlation_id: Optional trace identifier.
        flagged_for_summary: Whether this record should appear in daily summaries.
        created_at: UTC timestamp when the record was created.
    """

    agent_id: str
    tool_name: str
    risk_level: str
    outcome: str
    reason: str
    parameters: dict[str, Any]
    correlation_id: str | None = None
    flagged_for_summary: bool = False
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditTrail:
    """Append-only audit trail backed by PostgreSQL.

    Provides three operations:

    * :meth:`insert` — write a new record from an approval gate result.
    * :meth:`query` — retrieve records with optional filters.
    * :meth:`archive` — move records older than *n* days to an archive table.

    Args:
        pool: An initialised :class:`asyncpg.Pool` connected to the
            OsMEN-OC database.
        retention_days: Records older than this number of days will be moved
            to the ``audit_archive`` table when :meth:`archive` is called.
            Defaults to :data:`DEFAULT_RETENTION_DAYS`.
    """

    def __init__(self, pool: Pool, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        self._pool = pool
        self._retention_days = retention_days

    # ------------------------------------------------------------------
    # Insert
    # ------------------------------------------------------------------

    async def insert(self, record: AuditRecord) -> str:
        """Persist a new audit record.

        Args:
            record: The :class:`AuditRecord` to persist.

        Returns:
            The ``record_id`` of the inserted row.

        Raises:
            AuditError: If the database insert fails.
        """
        import json

        sql = """
            INSERT INTO audit_trail (
                record_id, agent_id, tool_name, risk_level,
                outcome, reason, parameters, correlation_id,
                flagged_for_summary, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    sql,
                    record.record_id,
                    record.agent_id,
                    record.tool_name,
                    record.risk_level,
                    record.outcome,
                    record.reason,
                    json.dumps(record.parameters),
                    record.correlation_id,
                    record.flagged_for_summary,
                    record.created_at,
                )
            logger.debug(
                "Audit record inserted id={} tool={} outcome={}",
                record.record_id,
                record.tool_name,
                record.outcome,
            )
            return record.record_id
        except Exception as exc:
            raise AuditError(
                f"Failed to insert audit record for tool {record.tool_name}: {exc}",
                correlation_id=record.correlation_id,
            ) from exc

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(
        self,
        *,
        agent_id: str | None = None,
        tool_name: str | None = None,
        outcome: str | None = None,
        flagged_only: bool = False,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Retrieve audit records with optional filters.

        Args:
            agent_id: Filter to a specific agent.
            tool_name: Filter to a specific tool.
            outcome: Filter to ``"approved"`` or ``"denied"``.
            flagged_only: When ``True``, return only records flagged for the
                daily summary.
            since: Return only records created after this UTC timestamp.
            limit: Maximum number of records to return.

        Returns:
            List of :class:`AuditRecord` objects ordered by ``created_at``
            descending.

        Raises:
            AuditError: If the database query fails.
        """
        import json

        conditions: list[str] = []
        params: list[Any] = []
        idx = 1

        if agent_id is not None:
            conditions.append(f"agent_id = ${idx}")
            params.append(agent_id)
            idx += 1
        if tool_name is not None:
            conditions.append(f"tool_name = ${idx}")
            params.append(tool_name)
            idx += 1
        if outcome is not None:
            conditions.append(f"outcome = ${idx}")
            params.append(outcome)
            idx += 1
        if flagged_only:
            conditions.append("flagged_for_summary = TRUE")
        if since is not None:
            conditions.append(f"created_at > ${idx}")
            params.append(since)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        # `where` contains only hardcoded condition templates with positional
        # asyncpg placeholders ($1…$N); no raw user input is ever interpolated.
        sql = f"""
            SELECT record_id, agent_id, tool_name, risk_level,
                   outcome, reason, parameters, correlation_id,
                   flagged_for_summary, created_at
            FROM audit_trail
            {where}
            ORDER BY created_at DESC
            LIMIT ${idx}
        """  # nosec B608

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
            return [
                AuditRecord(
                    record_id=row["record_id"],
                    agent_id=row["agent_id"],
                    tool_name=row["tool_name"],
                    risk_level=row["risk_level"],
                    outcome=row["outcome"],
                    reason=row["reason"],
                    parameters=json.loads(row["parameters"]),
                    correlation_id=row["correlation_id"],
                    flagged_for_summary=row["flagged_for_summary"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        except Exception as exc:
            raise AuditError(f"Failed to query audit trail: {exc}") from exc

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    async def archive(self, older_than_days: int | None = None) -> int:
        """Move old records to ``audit_archive`` and delete from live table.

        Args:
            older_than_days: Age threshold in days.  Records with
                ``created_at`` older than this many days are archived.
                Defaults to the instance's ``retention_days``.

        Returns:
            Number of records archived.

        Raises:
            AuditError: If the archive operation fails.
        """
        days = older_than_days if older_than_days is not None else self._retention_days
        cutoff = datetime.now(UTC) - timedelta(days=days)

        insert_sql = """
            INSERT INTO audit_archive
                SELECT * FROM audit_trail WHERE created_at < $1
        """
        delete_sql = "DELETE FROM audit_trail WHERE created_at < $1"

        try:
            async with self._pool.acquire() as conn, conn.transaction():
                await conn.execute(insert_sql, cutoff)
                result = await conn.execute(delete_sql, cutoff)
            # asyncpg returns "DELETE N" — extract the count
            archived = int(result.split()[-1]) if result else 0
            logger.info(
                "Archived {} audit records older than {} days (cutoff={})",
                archived,
                days,
                cutoff.isoformat(),
            )
            return archived
        except Exception as exc:
            raise AuditError(f"Failed to archive audit records: {exc}") from exc
