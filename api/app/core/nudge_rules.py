"""Deterministic nudge engine rules (TechSpec §5) — server-side source of truth.

The agent re-checks suppression client-side (defense in depth, P4); any change here
must ship with the table-driven tests in tests/test_nudge_rules.py updated to match.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

DEEP_WORK_GRACE_MIN = 15


def escalation_level(last_log_min_ago: int | None) -> int:
    """L0 < 60 min silent · L1 1–2 h · L2 2–4 h · L3 >= 4 h (TechSpec §5)."""
    if last_log_min_ago is None:
        return 3  # nothing logged today = maximum silence
    if last_log_min_ago < 60:
        return 0
    if last_log_min_ago < 120:
        return 1
    if last_log_min_ago < 240:
        return 2
    return 3


@dataclass(frozen=True)
class DeepWork:
    active: bool
    until: datetime | None  # block end (excl. grace); None when inactive


def deep_work_state(todays_logs: list[dict[str, Any]], now: datetime) -> DeepWork:
    """A declared block (data.block_minutes) silences nudges until end + 15 min grace."""
    for log in sorted(todays_logs, key=lambda x: x["ts"], reverse=True):
        minutes = (log.get("data") or {}).get("block_minutes")
        if not isinstance(minutes, int | float) or minutes <= 0:
            continue
        until = log["ts"] + timedelta(minutes=float(minutes))
        if now < until + timedelta(minutes=DEEP_WORK_GRACE_MIN):
            return DeepWork(active=True, until=until)
    return DeepWork(active=False, until=None)


def suppress(
    *,
    hour_ist: int,
    window_start: int,
    window_end: int,
    last_log_min_ago: int | None,
    last_nudge_min_ago: int | None,
    deep_work_active: bool,
    suppress_after_log_min: int = 25,
    nudge_min_gap_min: int = 50,
) -> str | None:
    """Return the (first) suppression reason, or None to allow. Order is contractual
    (AppFlow Flow 3): window -> recent log -> recent nudge -> deep work.
    Window is inclusive both ends: the 22:00 run is the last of the day (PRD F2)."""
    if not window_start <= hour_ist <= window_end:
        return "outside_window"
    if last_log_min_ago is not None and last_log_min_ago < suppress_after_log_min:
        return "recent_log"
    if last_nudge_min_ago is not None and last_nudge_min_ago < nudge_min_gap_min:
        return "recent_nudge"
    if deep_work_active:
        return "deep_work"
    return None


def streak_days(days_with_logs: set[Any], today: Any) -> int:
    """Consecutive days with >= 1 log, counting back from today (today itself may
    still be empty without breaking the streak — the day isn't over)."""
    if not days_with_logs:
        return 0
    day = today if today in days_with_logs else today - timedelta(days=1)
    n = 0
    while day in days_with_logs:
        n += 1
        day -= timedelta(days=1)
    return n
