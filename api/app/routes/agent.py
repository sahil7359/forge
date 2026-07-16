"""Agent-scope routes: GET /context · POST /nudges · POST /purge (TechSpec §3, §5)."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_agent
from app.config import settings
from app.core import purge as purge_core
from app.core.nudge_rules import deep_work_state, escalation_level, streak_days
from app.core.time import day_bounds_utc, day_counter, ist_day, month_bounds_utc, now_ist
from app.db import get_conn
from app.schemas import NudgeIn, PurgeIn

router = APIRouter(dependencies=[Depends(require_agent)])

STREAK_LOOKBACK_DAYS = 120


def parse_tomorrow_plan(md: str | None) -> list[str]:
    """Extract the '## Tomorrow's plan' bullets from a daily report (max 3)."""
    if not md:
        return []
    items: list[str] = []
    in_section = False
    for line in md.splitlines():
        if line.startswith("## "):
            in_section = line.lower().startswith("## tomorrow")
            continue
        if in_section:
            m = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)", line.strip())
            if m:
                items.append(m.group(1).strip())
    return items[:3]


@router.get("/context")
async def context(conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    now = now_ist()
    today = ist_day()
    start, end = day_bounds_utc(today)

    cfg = (
        await conn.execute(
            text(
                "select active_start, active_end, nudge_min_gap_min, suppress_after_log_min,"
                " hard_mode_after_hours, plan_day_anchor from settings"
            )
        )
    ).one_or_none()

    rows = list(
        await conn.execute(
            text("select ts, type, text, data from logs where ts >= :s and ts < :e order by ts"),
            {"s": start, "e": end},
        )
    )
    todays_logs = [
        {"ts": r.ts.astimezone(now.tzinfo), "type": r.type, "text": r.text, "data": r.data}
        for r in rows
    ]

    last_log_ts = (await conn.execute(text("select max(ts) from logs"))).scalar()
    last_log_min = (
        int((now - last_log_ts.astimezone(now.tzinfo)).total_seconds() // 60)
        if last_log_ts
        else None
    )

    nudge_rows = list(
        await conn.execute(
            text(
                "select ts, title, body from nudges where kind in ('hourly','fallback')"
                " order by ts desc limit 3"
            )
        )
    )
    last_nudge_min = (
        int((now - nudge_rows[0].ts.astimezone(now.tzinfo)).total_seconds() // 60)
        if nudge_rows
        else None
    )

    yesterday_md = (
        await conn.execute(
            text(
                "select md from reports where date = :d"
                " order by case kind when 'daily' then 0 else 1 end limit 1"
            ),
            {"d": today - timedelta(days=1)},
        )
    ).scalar()

    pending = list(
        await conn.execute(
            text("select title, created_ts from tasks where status='pending' order by created_ts")
        )
    )

    streak_src = await conn.execute(
        text("select ts from logs where ts >= :s"),
        {"s": now - timedelta(days=STREAK_LOOKBACK_DAYS)},
    )
    dw = deep_work_state(todays_logs, now)

    return {
        "now_ist": now.isoformat(),
        "day_counter": day_counter(cfg.plan_day_anchor) if cfg and cfg.plan_day_anchor else None,
        "day_total": settings.day_total,
        "streak": streak_days({ist_day(r.ts) for r in streak_src}, today),
        "window": {
            "start": cfg.active_start if cfg else 7,
            "end": cfg.active_end if cfg else 22,
        },
        "suppress_after_log_min": cfg.suppress_after_log_min if cfg else 25,
        "nudge_min_gap_min": cfg.nudge_min_gap_min if cfg else 50,
        "last_log_min_ago": last_log_min,
        "last_nudge_min_ago": last_nudge_min,
        "escalation": escalation_level(last_log_min),
        "deep_work": {"active": dw.active, "until": dw.until.isoformat() if dw.until else None},
        "todays_logs": [
            {"ts": item["ts"].isoformat(), "type": item["type"], "text": item["text"]}
            for item in todays_logs
        ],
        "pending_tasks": [
            {
                "title": t.title,
                "age_hours": round(
                    (now - t.created_ts.astimezone(now.tzinfo)).total_seconds() / 3600, 1
                ),
            }
            for t in pending
        ],
        "yesterday_plan": parse_tomorrow_plan(yesterday_md),
        "last_nudges": [f"{r.title} — {r.body}" for r in nudge_rows],
        "expenses_today": sum(
            float((item["data"] or {}).get("amount", 0))
            for item in todays_logs
            if item["type"] == "expense"
        ),
    }


@router.post("/nudges", status_code=201)
async def record_nudge(
    body: NudgeIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "insert into nudges (user_id, kind, title, body, escalation, model, latency_ms)"
                " values (:uid, :kind, :title, :body, :esc, :model, :lat) returning id, ts"
            ),
            {
                "uid": str(request.state.user_id),
                "kind": body.kind,
                "title": body.title,
                "body": body.body,
                "esc": body.escalation,
                "model": body.model,
                "lat": body.latency_ms,
            },
        )
    ).one()
    return {"id": str(row.id), "ts": row.ts.isoformat()}


class SqlPurgeRepo:
    """SQL adapter for the purge executor; all statements run in the request's
    single transaction (db.get_conn), so any raise rolls everything back."""

    def __init__(self, conn: AsyncConnection, ym: str) -> None:
        self.conn = conn
        self.ym = ym
        self.ts_start, self.ts_end = month_bounds_utc(ym)
        y, m = int(ym[:4]), int(ym[5:7])
        self.d_start = date(y, m, 1)
        self.d_end = date(y, m, calendar.monthrange(y, m)[1])

    async def archive_counts(self) -> dict[str, int] | None:
        row = (
            await self.conn.execute(
                text("select counts from monthly_archives where ym = :ym"), {"ym": self.ym}
            )
        ).scalar()
        return row

    async def live_counts(self) -> dict[str, int]:
        logs = (
            await self.conn.execute(
                text("select count(*) from logs where ts >= :s and ts < :e"),
                {"s": self.ts_start, "e": self.ts_end},
            )
        ).scalar()
        nudges = (
            await self.conn.execute(
                text("select count(*) from nudges where ts >= :s and ts < :e"),
                {"s": self.ts_start, "e": self.ts_end},
            )
        ).scalar()
        reports = (
            await self.conn.execute(
                text("select count(*) from reports where date >= :s and date <= :e"),
                {"s": self.d_start, "e": self.d_end},
            )
        ).scalar()
        return {"logs": int(logs or 0), "nudges": int(nudges or 0), "reports": int(reports or 0)}

    async def delete_month(self) -> dict[str, int]:
        logs = await self.conn.execute(
            text("delete from logs where ts >= :s and ts < :e"),
            {"s": self.ts_start, "e": self.ts_end},
        )
        nudges = await self.conn.execute(
            text("delete from nudges where ts >= :s and ts < :e"),
            {"s": self.ts_start, "e": self.ts_end},
        )
        reports = await self.conn.execute(
            text("delete from reports where date >= :s and date <= :e"),
            {"s": self.d_start, "e": self.d_end},
        )
        return {"logs": logs.rowcount, "nudges": nudges.rowcount, "reports": reports.rowcount}


@router.post("/purge")
async def purge_month(body: PurgeIn, conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    try:
        deleted = await purge_core.execute_purge(SqlPurgeRepo(conn, body.ym))
    except purge_core.DeleteMismatch as e:
        # raising aborts the transaction -> rollback; nothing was deleted
        raise HTTPException(500, {"code": e.code, "message": str(e)}) from e
    except purge_core.PurgeError as e:
        raise HTTPException(409, {"code": e.code, "message": str(e)}) from e
    return {"ym": body.ym, "purged": deleted}
