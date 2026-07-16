"""Reports + archives: user reads, agent writes (TechSpec §3)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_agent, require_user
from app.core.time import ist_day
from app.db import get_conn
from app.schemas import ArchiveIn, ReportIn

router = APIRouter()

MAX_RANGE_DAYS = 62


@router.get("/reports", dependencies=[Depends(require_user)])
async def list_reports(
    from_: date = Query(alias="from", default=None),
    to: date = Query(default=None),
    conn: AsyncConnection = Depends(get_conn),
) -> dict[str, Any]:
    to_d = to or ist_day()
    from_d = from_ or (to_d - timedelta(days=MAX_RANGE_DAYS))
    if to_d < from_d or (to_d - from_d).days > MAX_RANGE_DAYS:
        raise HTTPException(422, {"code": "validation_error", "message": "bad date range"})
    rows = await conn.execute(
        text(
            "select date, kind, left(md, 200) as preview, stats, created_ts from reports"
            " where date >= :f and date <= :t order by date desc, kind"
        ),
        {"f": from_d, "t": to_d},
    )
    return {
        "reports": [
            {
                "date": r.date.isoformat(),
                "kind": r.kind,
                "preview": r.preview,
                "stats": r.stats,
            }
            for r in rows
        ]
    }


@router.get("/reports/{report_date}", dependencies=[Depends(require_user)])
async def get_report(
    report_date: date, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "select date, kind, md, stats, model, created_ts from reports"
                " where date = :d order by case kind when 'daily' then 0 else 1 end limit 1"
            ),
            {"d": report_date},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "no report for that date"})
    return {
        "date": row.date.isoformat(),
        "kind": row.kind,
        "md": row.md,
        "stats": row.stats,
        "model": row.model,
    }


@router.post("/reports", status_code=201, dependencies=[Depends(require_agent)])
async def store_report(
    body: ReportIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "insert into reports (user_id, date, kind, md, stats, model)"
                " values (:uid, :date, :kind, :md, cast(:stats as jsonb), :model)"
                " on conflict (user_id, date, kind)"
                " do update set md = excluded.md, stats = excluded.stats, model = excluded.model"
                " returning id, date, kind"
            ),
            {
                "uid": str(request.state.user_id),
                "date": body.date,
                "kind": body.kind,
                "md": body.md,
                "stats": _json(body.stats),
                "model": body.model,
            },
        )
    ).one()
    return {"id": str(row.id), "date": row.date.isoformat(), "kind": row.kind}


@router.get("/archives", dependencies=[Depends(require_user)])
async def list_archives(conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    rows = await conn.execute(
        text("select ym, stats, counts, created_ts from monthly_archives order by ym desc")
    )
    return {
        "archives": [
            {
                "ym": r.ym,
                "stats": r.stats,
                "counts": r.counts,
                "created_ts": r.created_ts.isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/archives/{ym}", dependencies=[Depends(require_user)])
async def get_archive(ym: str, conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    row = (
        await conn.execute(
            text("select ym, md, raw, stats, counts from monthly_archives where ym = :ym"),
            {"ym": ym},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "no archive for that month"})
    return {"ym": row.ym, "md": row.md, "raw": row.raw, "stats": row.stats, "counts": row.counts}


@router.post("/archives/monthly", status_code=201, dependencies=[Depends(require_agent)])
async def store_archive(
    body: ArchiveIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "insert into monthly_archives (user_id, ym, md, raw, stats, counts)"
                " values (:uid, :ym, :md, cast(:raw as jsonb), cast(:stats as jsonb),"
                "         cast(:counts as jsonb))"
                " on conflict (user_id, ym) do update set md = excluded.md, raw = excluded.raw,"
                "   stats = excluded.stats, counts = excluded.counts"
                " returning id, ym"
            ),
            {
                "uid": str(request.state.user_id),
                "ym": body.ym,
                "md": body.md,
                "raw": _json(body.raw),
                "stats": _json(body.stats),
                "counts": _json(body.counts),
            },
        )
    ).one()
    return {"id": str(row.id), "ym": row.ym}


def _json(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data)
