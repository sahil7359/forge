"""IST day helpers for the agent — deliberate small duplicate of the API's
core/time.py (Rules R6 applies per deployable; the API remains the source of truth
for server-side windows, the agent only needs 'today', 'yesterday' and month spans)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def ist_today() -> date:
    return now_ist().date()


def ist_yesterday() -> date:
    return ist_today() - timedelta(days=1)


def prev_ym(today: date | None = None) -> str:
    t = today or ist_today()
    prev = t.replace(day=1) - timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


def month_span(ym: str) -> tuple[date, date]:
    """First and last IST calendar day of 'YYYY-MM'."""
    y, m = int(ym[:4]), int(ym[5:7])
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
