"""Purge invariant (Schema §5) — these tests are sacred; never weaken them (Rules R3.1)."""

from __future__ import annotations

import pytest
from app.core.purge import ArchiveMissing, CountMismatch, DeleteMismatch, execute_purge

GOOD = {"logs": 412, "nudges": 208, "reports": 28}


class FakeRepo:
    def __init__(self, archive, live=None, deleted=None):
        self.archive = archive
        self.live = live if live is not None else dict(GOOD)
        self.deleted = deleted if deleted is not None else dict(GOOD)
        self.calls: list[str] = []

    async def archive_counts(self):
        self.calls.append("archive_counts")
        return self.archive

    async def live_counts(self):
        self.calls.append("live_counts")
        return self.live

    async def delete_month(self):
        self.calls.append("delete_month")
        return self.deleted


@pytest.mark.asyncio
async def test_happy_path_deletes_only_after_verification():
    repo = FakeRepo(archive=dict(GOOD))
    assert await execute_purge(repo) == GOOD
    assert repo.calls == ["archive_counts", "live_counts", "delete_month"]


@pytest.mark.asyncio
async def test_missing_archive_never_deletes():
    repo = FakeRepo(archive=None)
    with pytest.raises(ArchiveMissing):
        await execute_purge(repo)
    assert "delete_month" not in repo.calls
    assert "live_counts" not in repo.calls  # bail immediately


@pytest.mark.asyncio
async def test_incomplete_archive_counts_never_deletes():
    repo = FakeRepo(archive={"logs": 412})  # nudges/reports counts absent
    with pytest.raises(ArchiveMissing):
        await execute_purge(repo)
    assert "delete_month" not in repo.calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "live",
    [
        {"logs": 411, "nudges": 208, "reports": 28},  # fewer than archived
        {"logs": 413, "nudges": 208, "reports": 28},  # more than archived
        {"logs": 412, "nudges": 208, "reports": 0},
    ],
)
async def test_count_mismatch_never_deletes(live):
    repo = FakeRepo(archive=dict(GOOD), live=live)
    with pytest.raises(CountMismatch):
        await execute_purge(repo)
    assert "delete_month" not in repo.calls


@pytest.mark.asyncio
async def test_delete_mismatch_raises_for_rollback():
    repo = FakeRepo(archive=dict(GOOD), deleted={"logs": 400, "nudges": 208, "reports": 28})
    with pytest.raises(DeleteMismatch):
        await execute_purge(repo)  # route maps this to an aborted transaction


@pytest.mark.asyncio
async def test_extra_archive_keys_ignored_but_core_three_enforced():
    archive = dict(GOOD, schema_version=1)
    repo = FakeRepo(archive=archive)
    assert await execute_purge(repo) == GOOD
