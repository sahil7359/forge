"""Month-close job — 1st, 00:25 IST (AppFlow Flow 6; Schema.md §4-5 is the law).

Run: python -m forge_agent.archive [--dry-run] [--ym YYYY-MM]
--dry-run builds and prints the archive summary without POSTing anything.

The agent only BUILDS the archive; verification and deletion live exclusively in the
API's /v1/purge (verify-before-purge invariant). Counts come from the same server
endpoint (/v1/export) that shares window logic with the purge — they cannot drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx
import structlog

from forge_agent.http import api_get, api_post
from forge_agent.istime import month_span, prev_ym
from forge_agent.nudge import send_to_all
from forge_agent.report import day_stats

log = structlog.get_logger()


def build_archive(ym: str, window: dict[str, Any]) -> dict[str, Any]:
    """Deterministic month archive: rendered md + verbatim raw + stats + counts.
    No LLM — the archive of record must never depend on model output."""
    logs, nudges, reports = window["logs"], window["nudges"], window["reports"]
    stats = day_stats(logs)
    days_active = len({entry["ts"][:10] for entry in logs})
    stats["days_active"] = days_active

    md_lines = [
        f"# Forge — monthly archive {ym}",
        "",
        f"- logs: {window['counts']['logs']}",
        f"- nudges: {window['counts']['nudges']}",
        f"- daily reports: {window['counts']['reports']}",
        f"- active days: {days_active}",
        f"- expenses total: ₹{stats['expenses_total']:.0f}",
        f"- deep-work minutes: {stats['deep_work_minutes']:.0f}",
        f"- workouts: {stats['workouts']}",
        "",
        "## Daily reports",
        "",
    ]
    for r in reports:
        md_lines += [f"### {r['date']} ({r['kind']})", "", r["md"], ""]
    md = "\n".join(md_lines)

    return {
        "ym": ym,
        "md": md,
        "raw": {"logs": logs, "nudges": nudges, "reports": reports},
        "stats": stats,
        "counts": window["counts"],  # server-computed — purge verifies against these
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ym", default=None)
    args = parser.parse_args()

    ym = args.ym or prev_ym()
    first, last = month_span(ym)
    window = api_get(f"/v1/export?from={first.isoformat()}&to={last.isoformat()}")
    archive = build_archive(ym, window)

    if args.dry_run:
        print(json.dumps({"ym": ym, "counts": archive["counts"], "stats": archive["stats"]}))
        log.info("dry_run_only", ym=ym, counts=archive["counts"])
        return 0

    api_post("/v1/archives/monthly", archive)
    try:
        purged = api_post("/v1/purge", {"ym": ym})
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:200]
        log.error("purge_refused", ym=ym, status=e.response.status_code, detail=detail)
        send_to_all("Archive verify failed", f"{ym}: purge refused — nothing deleted. Check API.")
        return 1
    counts = (purged or {}).get("purged", {})
    send_to_all(
        f"{ym} archived",
        f"{counts.get('logs', 0)} logs, {counts.get('reports', 0)} reports archived & purged.",
    )
    log.info("month_closed", ym=ym, purged=counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
