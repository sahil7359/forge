"""All IST day-boundary math lives here — never inline elsewhere (Rules.md R6).

DB stores UTC; a product 'day' is [00:00, 24:00) IST; months close on IST boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def now_ist() -> datetime:
    return datetime.now(IST)


def ist_day(dt: datetime | None = None) -> date:
    """The IST calendar day containing dt (default: now)."""
    return (dt.astimezone(IST) if dt else now_ist()).date()


def day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    """UTC half-open interval [start, end) covering IST day d."""
    start = datetime(d.year, d.month, d.day, tzinfo=IST)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def ym_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_bounds_utc(ym: str) -> tuple[datetime, datetime]:
    """UTC half-open interval covering IST month 'YYYY-MM'. Purge scope = exactly this window."""
    y, m = int(ym[:4]), int(ym[5:7])
    start = datetime(y, m, 1, tzinfo=IST)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return start.astimezone(UTC), datetime(ny, nm, 1, tzinfo=IST).astimezone(UTC)


def prev_ym(today: date | None = None) -> str:
    """Month to archive when the 1st-of-month job runs."""
    t = today or ist_day()
    return ym_of(t.replace(day=1) - timedelta(days=1))


def day_counter(anchor: date, today: date | None = None) -> int:
    """Day N of the plan (anchor day = Day 1). settings.plan_day_anchor."""
    return ((today or ist_day()) - anchor).days + 1
