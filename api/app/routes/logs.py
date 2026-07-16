"""POST /logs · GET /logs · GET /today (TechSpec §3)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_user
from app.config import settings
from app.core.nudge_rules import streak_days
from app.core.time import day_bounds_utc, ist_day, now_ist
from app.db import get_conn
from app.schemas import LogIn

router = APIRouter(dependencies=[Depends(require_user)])

DAILY_LOG_QUOTA = 500
MAX_RANGE_DAYS = 62
STREAK_LOOKBACK_DAYS = 120


def _row_out(r: Any) -> dict[str, Any]:
    return {"id": str(r.id), "ts": r.ts.isoformat(), "type": r.type, "text": r.text, "data": r.data}


async def _today_logs(conn: AsyncConnection) -> list[Any]:
    start, end = day_bounds_utc(ist_day())
    rows = await conn.execute(
        text("select id, ts, type, text, data from logs where ts >= :s and ts < :e order by ts"),
        {"s": start, "e": end},
    )
    return list(rows)


async def _streak(conn: AsyncConnection) -> int:
    since = now_ist() - timedelta(days=STREAK_LOOKBACK_DAYS)
    rows = await conn.execute(text("select ts from logs where ts >= :s"), {"s": since})
    days = {ist_day(r.ts) for r in rows}
    return streak_days(days, ist_day())


def _stats(today_rows: list[Any]) -> dict[str, Any]:
    expenses = sum(
        float((r.data or {}).get("amount", 0)) for r in today_rows if r.type == "expense"
    )
    deep_work = sum(
        float((r.data or {}).get("block_minutes", 0))
        for r in today_rows
        if (r.data or {}).get("block_minutes")
    )
    return {
        "log_count": len(today_rows),
        "expenses_today": expenses,
        "deep_work_minutes": deep_work,
        "workouts": sum(1 for r in today_rows if r.type == "fitness"),
    }


@router.post("/logs", status_code=201)
async def create_log(
    body: LogIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    start, _ = day_bounds_utc(ist_day())
    count = (
        await conn.execute(text("select count(*) from logs where ts >= :s"), {"s": start})
    ).scalar()
    if count is not None and count >= DAILY_LOG_QUOTA:
        raise HTTPException(429, {"code": "quota_exceeded", "message": "daily log quota reached"})

    inserted = await conn.execute(
        text(
            "insert into logs (id, user_id, ts, type, text, data, source)"
            " values (:id, :uid, coalesce(:ts, now()), :type, :text, cast(:data as jsonb), 'pwa')"
            " on conflict (id) do nothing returning id"
        ),
        {
            "id": str(body.id),
            "uid": str(request.state.user_id),
            "ts": body.ts,
            "type": body.type,
            "text": body.text,
            "data": _json(body.data),
        },
    )
    replay = inserted.scalar() is None  # duplicate offline replay -> no-op (AppFlow Flow 9)
    row = (
        await conn.execute(
            text("select id, ts, type, text, data from logs where id = :id"), {"id": str(body.id)}
        )
    ).one()
    return {**_row_out(row), "replayed": replay}


@router.get("/logs")
async def list_logs(
    from_: date = Query(alias="from", default_factory=ist_day),
    to: date = Query(default_factory=ist_day),
    conn: AsyncConnection = Depends(get_conn),
) -> dict[str, Any]:
    if to < from_ or (to - from_).days > MAX_RANGE_DAYS:
        raise HTTPException(422, {"code": "validation_error", "message": "bad date range"})
    start, _ = day_bounds_utc(from_)
    _, end = day_bounds_utc(to)
    rows = await conn.execute(
        text("select id, ts, type, text, data from logs where ts >= :s and ts < :e order by ts"),
        {"s": start, "e": end},
    )
    return {"logs": [_row_out(r) for r in rows]}


@router.get("/today")
async def today(conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    rows = await _today_logs(conn)
    anchor_row = await conn.execute(text("select plan_day_anchor from settings"))
    anchor = anchor_row.scalar()
    pending = await conn.execute(
        text("select id, title, created_ts from tasks where status = 'pending' order by created_ts")
    )
    now = now_ist()
    return {
        "date": ist_day().isoformat(),
        "day_counter": _day_counter(anchor),
        "day_total": settings.day_total,
        "streak": await _streak(conn),
        "stats": _stats(rows),
        "logs": [_row_out(r) for r in rows],
        "pending_tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "age_hours": round(
                    (now - t.created_ts.astimezone(now.tzinfo)).total_seconds() / 3600, 1
                ),
            }
            for t in pending
        ],
    }


def _day_counter(anchor: date | None) -> int | None:
    from app.core.time import day_counter

    return day_counter(anchor) if anchor else None


def _json(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data)
