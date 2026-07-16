"""Shared fixture context for agent tests — a realistic day (mirrors POC S2)."""

from __future__ import annotations

import pytest

FIXTURE_CTX = {
    "now_ist": "2026-07-16T15:00:00+05:30",
    "day_counter": 2,
    "day_total": 84,
    "streak": 1,
    "window": {"start": 7, "end": 22},
    "suppress_after_log_min": 25,
    "nudge_min_gap_min": 50,
    "last_log_min_ago": 130,
    "last_nudge_min_ago": 55,
    "escalation": 2,
    "deep_work": {"active": False, "until": None},
    "todays_logs": [
        {
            "ts": "2026-07-16T09:10:00+05:30",
            "type": "checkin",
            "text": "morning review done, starting the API auth module",
        },
        {
            "ts": "2026-07-16T10:45:00+05:30",
            "type": "task",
            "text": "write token validation tests",
        },
    ],
    "pending_tasks": [{"title": "write token validation tests", "age_hours": 4.3}],
    "yesterday_plan": ["finish auth module", "deploy API to staging", "30 min workout"],
    "last_nudges": ["Day 2/84 - auth is moving — Next: token validation tests."],
    "expenses_today": 250,
}


@pytest.fixture
def ctx() -> dict:
    return {k: (v.copy() if isinstance(v, dict | list) else v) for k, v in FIXTURE_CTX.items()}
