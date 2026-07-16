"""Client-side suppression mirror — must match api/app/core/nudge_rules.py (Rules R5)."""

from __future__ import annotations

import pytest
from forge_agent.rules import quiet_hour, suppress


@pytest.mark.parametrize(
    ("hour", "overrides", "expected"),
    [
        (6, {}, "outside_window"),
        (23, {}, "outside_window"),
        (7, {}, None),
        (22, {}, None),  # 22:00 inclusive — the last run of the day
        (12, {"last_log_min_ago": 10}, "recent_log"),
        (12, {"last_log_min_ago": 24}, "recent_log"),
        (12, {"last_log_min_ago": 25}, None),
        (12, {"last_nudge_min_ago": 30}, "recent_nudge"),
        (12, {"last_nudge_min_ago": 50}, None),
        (12, {"deep_work": {"active": True, "until": None}}, "deep_work"),
        (12, {"last_log_min_ago": None, "last_nudge_min_ago": None}, None),  # fresh day
        (6, {"last_log_min_ago": 10}, "outside_window"),  # precedence: window first
        (12, {"last_log_min_ago": 10, "deep_work": {"active": True}}, "recent_log"),
    ],
)
def test_suppression_matrix(ctx, hour, overrides, expected):
    base = dict(ctx, last_log_min_ago=130, last_nudge_min_ago=55)
    base.update(overrides)
    assert suppress(base, hour) == expected


def test_custom_settings_respected(ctx):
    ctx.update(suppress_after_log_min=40, last_log_min_ago=30)
    assert suppress(ctx, 12) == "recent_log"
    ctx.update(last_log_min_ago=45)
    assert suppress(ctx, 12) is None


def test_quiet_hour_all_calm(ctx):
    ctx.update(escalation=0, pending_tasks=[], last_nudge_min_ago=55)
    assert quiet_hour(ctx) is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"escalation": 1},
        {"pending_tasks": [{"title": "x", "age_hours": 1}]},
        {"last_nudge_min_ago": 80},
        {"last_nudge_min_ago": None},
    ],
)
def test_quiet_hour_not_when(ctx, overrides):
    ctx.update(escalation=0, pending_tasks=[], last_nudge_min_ago=55)
    ctx.update(overrides)
    assert quiet_hour(ctx) is False
