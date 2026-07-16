"""Fallback layer decisions — 'Rig 2 off' hour must produce exactly one nudge (P5 DoD)."""

from __future__ import annotations

import pytest
from forge_agent.fallback import nudge_decision, stats_report_md, template


@pytest.mark.parametrize(
    ("hour", "overrides", "expected"),
    [
        # Rig 2 alive: its :00 nudge is ~20 min old at :20 -> never double-send
        (12, {"last_nudge_min_ago": 20}, "rig2_alive"),
        (12, {"last_nudge_min_ago": 69}, "rig2_alive"),
        # Rig 2 off but user active -> no nag
        (12, {"last_nudge_min_ago": 80, "last_log_min_ago": 30}, "user_active"),
        # Rig 2 off, user silent -> send
        (12, {"last_nudge_min_ago": 80, "last_log_min_ago": 90}, None),
        (12, {"last_nudge_min_ago": None, "last_log_min_ago": None}, None),  # fresh day, rig off
        # window edges (inclusive)
        (6, {"last_nudge_min_ago": 80, "last_log_min_ago": 90}, "outside_window"),
        (22, {"last_nudge_min_ago": 80, "last_log_min_ago": 90}, None),
        (23, {"last_nudge_min_ago": 80, "last_log_min_ago": 90}, "outside_window"),
    ],
)
def test_nudge_decision(ctx, hour, overrides, expected):
    ctx.update(last_nudge_min_ago=80, last_log_min_ago=90)
    ctx.update(overrides)
    assert nudge_decision(ctx, hour) == expected


def test_template_within_push_caps(ctx):
    title, body = template(ctx)
    assert len(title) <= 40
    assert len(body) <= 220
    assert "130 min" in body  # references real silence from context


def test_template_handles_empty_context():
    title, body = template({})
    assert "a while" in body


def test_stats_report_md_structure():
    logs = [
        {"ts": "2026-07-15T09:10:00+05:30", "type": "checkin", "text": "shipped auth"},
        {"ts": "2026-07-15T18:00:00+05:30", "type": "expense", "text": "dinner"},
    ]
    stats = {"log_count": 2, "expenses_total": 250.0, "deep_work_minutes": 0, "workouts": 0}
    md = stats_report_md("2026-07-15", stats, logs)
    assert "stats-only report" in md
    assert "- logs: 2" in md
    assert "09:10 checkin: shipped auth" in md
    assert "## Tomorrow's plan" in md  # section contract kept so the PWA renders consistently
