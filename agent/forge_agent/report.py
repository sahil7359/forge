"""Midnight report job — 00:05 IST, retried by a 07:00 trigger (AppFlow Flow 5).

Run: python -m forge_agent.report
Idempotent: exits quietly when yesterday's 'daily' report already exists, so the
07:00 retry task never double-writes (the API upsert would also absorb it).
"""

from __future__ import annotations

import sys
from typing import Any

import structlog

from forge_agent import context, llm
from forge_agent.config import settings
from forge_agent.http import api_get, api_post
from forge_agent.istime import ist_yesterday
from forge_agent.nudge import send_to_all

log = structlog.get_logger()


def day_stats(logs: list[dict[str, Any]]) -> dict[str, Any]:
    expenses = sum(
        float((entry.get("data") or {}).get("amount", 0))
        for entry in logs
        if entry.get("type") == "expense"
    )
    minutes = sum(
        float((entry.get("data") or {}).get("block_minutes", 0))
        for entry in logs
        if (entry.get("data") or {}).get("block_minutes")
    )
    return {
        "log_count": len(logs),
        "expenses_total": expenses,
        "deep_work_minutes": minutes,
        "workouts": sum(1 for entry in logs if entry.get("type") == "fitness"),
    }


def main() -> int:
    day = ist_yesterday().isoformat()
    window = api_get(f"/v1/export?from={day}&to={day}")
    if any(r["kind"] == "daily" for r in window["reports"]):
        log.info("report_exists", date=day)
        return 0

    ctx = api_get("/v1/context")  # day counter / streak / pending come from the live bundle
    stats = day_stats(window["logs"])
    system, user = context.build_report_prompt(
        day,
        {
            "logs": window["logs"],
            "day_counter": ctx.get("day_counter"),
            "day_total": ctx.get("day_total"),
            "streak": ctx.get("streak"),
            "pending_tasks": ctx.get("pending_tasks", []),
        },
        stats,
    )
    try:
        md, latency = llm.report_md(system, user)
    except llm.LLMUnavailable as e:
        log.warning("ollama_down_retry_at_0700", error=str(e))
        return 1  # non-zero so the miss is visible; 07:00 task retries, 00:45 fallback covered
    except llm.LLMFallback as e:
        log.warning("empty_report_retry_at_0700", error=str(e))
        return 1

    api_post(
        "/v1/reports",
        {"date": day, "kind": "daily", "md": md, "stats": stats, "model": settings.model},
    )
    day_no = ctx.get("day_counter")
    title = f"Day {day_no} report ready" if day_no else "Daily report ready"
    body = f"{stats['log_count']} logs · ₹{stats['expenses_total']:.0f} — plan for tomorrow inside."
    send_to_all(title[:40], body[:220])
    api_post(
        "/v1/nudges",
        {
            "kind": "report_ready",
            "title": title[:40],
            "body": body[:220],
            "escalation": 0,
            "model": settings.model,
            "latency_ms": latency,
        },
    )
    log.info("report_stored", date=day, latency_ms=latency)
    return 0


if __name__ == "__main__":
    sys.exit(main())
