"""Verify-before-purge executor (Schema.md §5 — the sacred invariant).

PROPOSAL under Rules.md R1: purge logic is owner-written/approved. This module is the
draft for Sahil's line-by-line review; the tests in tests/test_purge.py encode the
invariant and must never be weakened.

The executor is pure orchestration over a narrow repo protocol so the invariant is
CI-testable without Postgres; the SQL lives in routes/agent.py (SqlPurgeRepo).
"""

from __future__ import annotations

from typing import Protocol

TABLES = ("logs", "nudges", "reports")


class PurgeError(Exception):
    code = "purge_failed"


class ArchiveMissing(PurgeError):
    code = "archive_missing"


class CountMismatch(PurgeError):
    code = "count_mismatch"


class DeleteMismatch(PurgeError):
    code = "delete_mismatch"


class PurgeRepo(Protocol):
    async def archive_counts(self) -> dict[str, int] | None:
        """counts jsonb of the archive row for (user, ym), or None if absent."""
        ...

    async def live_counts(self) -> dict[str, int]:
        """Current row counts per table inside the month window."""
        ...

    async def delete_month(self) -> dict[str, int]:
        """Delete the month's rows; MUST run inside the caller's transaction.
        Returns deleted-row counts per table."""
        ...


async def execute_purge(repo: PurgeRepo) -> dict[str, int]:
    """Invariant: no verified archive -> no deletion, ever.

    1. Archive row must exist            -> else ArchiveMissing, nothing touched.
    2. Live counts == archive counts     -> else CountMismatch, nothing touched.
    3. Deleted counts == archive counts  -> else DeleteMismatch; caller MUST roll
       back the surrounding transaction (routes/agent.py maps this to 409 + no commit).
    """
    archived = await repo.archive_counts()
    if archived is None:
        raise ArchiveMissing("no archive row; refusing to delete anything")
    expected = {t: int(archived.get(t, -1)) for t in TABLES}
    if any(v < 0 for v in expected.values()):
        raise ArchiveMissing(f"archive counts incomplete: {archived}")

    live = await repo.live_counts()
    if live != expected:
        raise CountMismatch(f"live {live} != archived {expected}")

    deleted = await repo.delete_month()
    if deleted != expected:
        raise DeleteMismatch(f"deleted {deleted} != archived {expected}")
    return deleted
