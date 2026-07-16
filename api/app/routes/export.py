"""GET /v1/export?from&to (agent) — verbatim day-window dump for the report and
archive jobs (P4). The agent never touches the DB (Rig 2 pull-only, single trust
path), so this is its only bulk read. Counts are computed here with the same window
logic the purge uses, so archive counts and purge verification can never drift.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_agent
from app.core.time import day_bounds_utc
from app.db import get_conn

router = APIRouter(dependencies=[Depends(require_agent)])

MAX_RANGE_DAYS = 62


@router.get("/export")
async def export_window(
    from_: date = Query(alias="from"),
    to: date = Query(),
    conn: AsyncConnection = Depends(get_conn),
) -> dict[str, Any]:
    if to < from_ or (to - from_).days > MAX_RANGE_DAYS:
        raise HTTPException(422, {"code": "validation_error", "message": "bad date range"})
    ts_start, _ = day_bounds_utc(from_)
    _, ts_end = day_bounds_utc(to)

    logs = list(
        await conn.execute(
            text(
                "select id, ts, type, text, data, source from logs"
                " where ts >= :s and ts < :e order by ts"
            ),
            {"s": ts_start, "e": ts_end},
        )
    )
    nudges = list(
        await conn.execute(
            text(
                "select ts, kind, title, body, escalation, model, latency_ms from nudges"
                " where ts >= :s and ts < :e order by ts"
            ),
            {"s": ts_start, "e": ts_end},
        )
    )
    reports = list(
        await conn.execute(
            text(
                "select date, kind, md, stats, model, created_ts from reports"
                " where date >= :f and date <= :t order by date, kind"
            ),
            {"f": from_, "t": to},
        )
    )
    return {
        "from": from_.isoformat(),
        "to": to.isoformat(),
        "logs": [
            {
                "id": str(r.id),
                "ts": r.ts.isoformat(),
                "type": r.type,
                "text": r.text,
                "data": r.data,
                "source": r.source,
            }
            for r in logs
        ],
        "nudges": [
            {
                "ts": r.ts.isoformat(),
                "kind": r.kind,
                "title": r.title,
                "body": r.body,
                "escalation": r.escalation,
                "model": r.model,
                "latency_ms": r.latency_ms,
            }
            for r in nudges
        ],
        "reports": [
            {
                "date": r.date.isoformat(),
                "kind": r.kind,
                "md": r.md,
                "stats": r.stats,
                "model": r.model,
                "created_ts": r.created_ts.isoformat(),
            }
            for r in reports
        ],
        "counts": {"logs": len(logs), "nudges": len(nudges), "reports": len(reports)},
    }
