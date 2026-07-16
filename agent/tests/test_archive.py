"""Archive builder dry-run on a fixture month — the P4 DoD counts check."""

from __future__ import annotations

from datetime import date

from forge_agent.archive import build_archive
from forge_agent.istime import month_span, prev_ym

FIXTURE_WINDOW = {
    "from": "2026-06-01",
    "to": "2026-06-30",
    "logs": [
        {
            "id": "a",
            "ts": "2026-06-01T09:00:00+05:30",
            "type": "checkin",
            "text": "first",
            "data": {},
            "source": "pwa",
        },
        {
            "id": "b",
            "ts": "2026-06-01T18:00:00+05:30",
            "type": "expense",
            "text": "groceries",
            "data": {"amount": 480},
            "source": "pwa",
        },
        {
            "id": "c",
            "ts": "2026-06-02T10:00:00+05:30",
            "type": "fitness",
            "text": "30 min run",
            "data": {},
            "source": "pwa",
        },
    ],
    "nudges": [
        {
            "ts": "2026-06-01T10:00:00+05:30",
            "kind": "hourly",
            "title": "Day 1",
            "body": "go",
            "escalation": 0,
            "model": "m",
            "latency_ms": 900,
        }
    ],
    "reports": [
        {
            "date": "2026-06-01",
            "kind": "daily",
            "md": "## Shipped today\n- first",
            "stats": {},
            "model": "m",
            "created_ts": "2026-06-02T00:05:00+05:30",
        }
    ],
    "counts": {"logs": 3, "nudges": 1, "reports": 1},
}


def test_counts_passed_through_verbatim():
    archive = build_archive("2026-06", FIXTURE_WINDOW)
    # counts MUST be the server's numbers untouched — purge verifies against them
    assert archive["counts"] == {"logs": 3, "nudges": 1, "reports": 1}


def test_raw_is_verbatim_with_all_timestamps():
    archive = build_archive("2026-06", FIXTURE_WINDOW)
    assert archive["raw"]["logs"] == FIXTURE_WINDOW["logs"]
    assert archive["raw"]["nudges"][0]["ts"] == "2026-06-01T10:00:00+05:30"
    assert archive["raw"]["reports"][0]["created_ts"] == "2026-06-02T00:05:00+05:30"


def test_md_summarizes_month_and_embeds_daily_reports():
    archive = build_archive("2026-06", FIXTURE_WINDOW)
    md = archive["md"]
    assert "monthly archive 2026-06" in md
    assert "logs: 3" in md
    assert "expenses total: ₹480" in md
    assert "### 2026-06-01 (daily)" in md
    assert "- first" in md
    assert archive["stats"]["days_active"] == 2


def test_month_span_and_prev_ym():
    assert month_span("2026-06") == (date(2026, 6, 1), date(2026, 6, 30))
    assert month_span("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))
    assert prev_ym(date(2026, 7, 16)) == "2026-06"
    assert prev_ym(date(2026, 1, 1)) == "2025-12"
