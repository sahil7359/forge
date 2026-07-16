"""GitHub Actions entrypoints (AppFlow Flow 7) — LLM-free by design.

Usage: python -m forge_agent.fallback {nudge|report}
Config comes from env vars in the workflow (API_BASE, AGENT_TOKEN, VAPID_PRIVATE_KEY,
VAPID_SUBJECT) — pydantic-settings reads them natively; no .env on runners.
"""

from __future__ import annotations

import sys

import httpx
import structlog

from forge_agent.config import settings
from forge_agent.http import api_get, api_post
from forge_agent.istime import ist_today, prev_ym
from forge_agent.nudge import send_to_all
from forge_agent.report import day_stats

log = structlog.get_logger()

SILENCE_MIN = 70  # no nudge AND no log in the last 70 min -> Rig 2 looks offline (TechSpec §4)


def nudge_decision(ctx: dict, hour_ist: int) -> str | None:
    """Skip reason, or None to send the template nudge. Never double-sends while
    Rig 2 is alive: its :00 nudge is < 70 min old when this runs at :20."""
    window = ctx.get("window") or {}
    if not int(window.get("start", 7)) <= hour_ist <= int(window.get("end", 22)):
        return "outside_window"
    last_nudge = ctx.get("last_nudge_min_ago")
    if last_nudge is not None and last_nudge < SILENCE_MIN:
        return "rig2_alive"
    last_log = ctx.get("last_log_min_ago")
    if last_log is not None and last_log < SILENCE_MIN:
        return "user_active"
    return None


def template(ctx: dict) -> tuple[str, str]:
    minutes = ctx.get("last_log_min_ago")
    since = f"{minutes} min" if minutes is not None else "a while"
    return (
        "No coach this hour",
        f"Rig 2 looks offline. What moved in the last {since}? One line.",
    )


def stats_report_md(day: str, stats: dict, logs: list[dict]) -> str:
    lines = [
        f"# {day} — stats-only report (Rig 2 was off)",
        "",
        "## Numbers",
        f"- logs: {stats['log_count']}",
        f"- expenses: ₹{stats['expenses_total']:.0f}",
        f"- deep-work minutes: {stats['deep_work_minutes']:.0f}",
        f"- workouts: {stats['workouts']}",
        "",
        "## Logged",
    ]
    lines += [f"- {entry['ts'][11:16]} {entry['type']}: {entry['text']}" for entry in logs]
    lines += ["", "## Tomorrow's plan", "- (no coach tonight — pick up this morning)"]
    return "\n".join(lines)


def archive_exists(ym: str) -> bool:
    r = httpx.get(
        f"{settings.api_base}/v1/archives/{ym}",
        headers={"Authorization": f"Bearer {settings.agent_token}"},
        timeout=150,
    )
    if r.status_code == 404:
        return False
    r.raise_for_status()
    return True


def run_nudge() -> int:
    ctx = api_get("/v1/context")
    from datetime import datetime

    hour = datetime.fromisoformat(ctx["now_ist"]).hour
    reason = nudge_decision(ctx, hour)
    if reason:
        log.info("fallback_skip", reason=reason)
        return 0
    title, body = template(ctx)
    send_to_all(title, body)
    api_post(
        "/v1/nudges",
        {"kind": "fallback", "title": title, "body": body, "escalation": ctx.get("escalation", 0)},
    )
    log.info("fallback_nudge_sent")
    return 0


def run_report() -> int:
    from forge_agent.istime import ist_yesterday

    day = ist_yesterday().isoformat()
    window = api_get(f"/v1/export?from={day}&to={day}")
    if window["reports"]:
        log.info("report_exists", date=day)  # any kind counts — Rig 2 or a previous fallback
    else:
        stats = day_stats(window["logs"])
        md = stats_report_md(day, stats, window["logs"])
        api_post(
            "/v1/reports",
            {"date": day, "kind": "daily_fallback", "md": md, "stats": stats},
        )
        send_to_all(
            "Daily report (stats-only)",
            f"{stats['log_count']} logs yesterday. Rig 2 was off — no coach notes.",
        )
        log.info("fallback_report_stored", date=day)

    if ist_today().day == 1:  # month-close watchdog (AppFlow Flow 7c)
        ym = prev_ym()
        if not archive_exists(ym):
            send_to_all("Month-close didn't run", f"No archive for {ym}. Check Rig 2 + API.")
            log.error("archive_missing_alert", ym=ym)
            return 1
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "nudge":
        return run_nudge()
    if mode == "report":
        return run_report()
    print("usage: python -m forge_agent.fallback {nudge|report}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
