"""Client-side suppression re-check — defense in depth (AppFlow Flow 3 step 2).

Mirrors api/app/core/nudge_rules.py, which is the source of truth; any change there
must be mirrored here and in tests/test_suppression.py."""

from __future__ import annotations

from typing import Any


def suppress(ctx: dict[str, Any], hour_ist: int) -> str | None:
    """First matching suppression reason from the /v1/context bundle, or None."""
    window = ctx.get("window") or {}
    start, end = int(window.get("start", 7)), int(window.get("end", 22))
    if not start <= hour_ist <= end:  # inclusive both ends: 22:00 is the last run
        return "outside_window"
    last_log = ctx.get("last_log_min_ago")
    if last_log is not None and last_log < int(ctx.get("suppress_after_log_min", 25)):
        return "recent_log"
    last_nudge = ctx.get("last_nudge_min_ago")
    if last_nudge is not None and last_nudge < int(ctx.get("nudge_min_gap_min", 50)):
        return "recent_nudge"
    if (ctx.get("deep_work") or {}).get("active"):
        return "deep_work"
    return None


def quiet_hour(ctx: dict[str, Any]) -> bool:
    """Skip when everything is calm: fully engaged (L0), nothing pending, and the
    previous hour already produced a nudge — silence beats noise."""
    return (
        ctx.get("escalation") == 0
        and not ctx.get("pending_tasks")
        and ctx.get("last_nudge_min_ago") is not None
        and ctx["last_nudge_min_ago"] < 70
    )
