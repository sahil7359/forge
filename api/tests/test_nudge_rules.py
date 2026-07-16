"""Table-driven suppression matrix, escalation ladder, deep work, streak (Rules R5)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from app.core.nudge_rules import (
    DeepWork,
    deep_work_state,
    escalation_level,
    streak_days,
    suppress,
)
from app.core.time import IST


@pytest.mark.parametrize(
    ("minutes", "level"),
    [
        (None, 3),  # nothing ever logged = max silence
        (0, 0),
        (59, 0),
        (60, 1),
        (119, 1),
        (120, 2),
        (239, 2),
        (240, 3),
        (1000, 3),
    ],
)
def test_escalation_ladder(minutes, level):
    assert escalation_level(minutes) == level


@pytest.mark.parametrize(
    ("hour", "log_min", "nudge_min", "dw", "expected"),
    [
        (6, 300, 300, False, "outside_window"),  # before window
        (23, 300, 300, False, "outside_window"),  # after window
        (7, 300, 300, False, None),  # first hour allowed
        (22, 300, 300, False, None),  # 22:00 is the last run, inclusive
        (12, 10, 300, False, "recent_log"),  # rule 2: < 25 min since log
        (12, 24, 300, False, "recent_log"),
        (12, 25, 300, False, None),  # exactly at threshold -> allow
        (12, 300, 30, False, "recent_nudge"),  # rule 3: < 50 min since nudge
        (12, 300, 49, False, "recent_nudge"),
        (12, 300, 50, False, None),
        (12, 300, 300, True, "deep_work"),  # rule 4
        (12, None, None, False, None),  # fresh day, nothing logged, no nudge yet
        (6, 10, 10, True, "outside_window"),  # precedence: window first
        (12, 10, 10, True, "recent_log"),  # then recent log
        (12, 300, 10, True, "recent_nudge"),  # then recent nudge
    ],
)
def test_suppression_matrix(hour, log_min, nudge_min, dw, expected):
    assert (
        suppress(
            hour_ist=hour,
            window_start=7,
            window_end=22,
            last_log_min_ago=log_min,
            last_nudge_min_ago=nudge_min,
            deep_work_active=dw,
        )
        == expected
    )


def _log(hour: int, minute: int, block: int | None = None):
    ts = datetime(2026, 7, 16, hour, minute, tzinfo=IST)
    return {
        "ts": ts,
        "type": "checkin",
        "text": "x",
        "data": {"block_minutes": block} if block else {},
    }


def _now(hour: int, minute: int) -> datetime:
    return datetime(2026, 7, 16, hour, minute, tzinfo=IST)


def test_deep_work_active_during_block():
    state = deep_work_state([_log(14, 0, block=120)], _now(15, 0))
    assert state == DeepWork(active=True, until=datetime(2026, 7, 16, 16, 0, tzinfo=IST))


def test_deep_work_grace_15min_after_block_end():
    assert deep_work_state([_log(14, 0, block=120)], _now(16, 10)).active is True
    assert deep_work_state([_log(14, 0, block=120)], _now(16, 16)).active is False


def test_deep_work_ignores_normal_logs_and_bad_values():
    logs = [
        _log(14, 0),
        {"ts": _now(14, 30), "type": "checkin", "text": "x", "data": {"block_minutes": "soon"}},
    ]
    assert deep_work_state(logs, _now(14, 40)).active is False
    assert deep_work_state([], _now(12, 0)).active is False


def test_streak_counts_back_from_today():
    today = date(2026, 7, 16)
    days = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert streak_days(days, today) == 3


def test_streak_today_empty_does_not_break():
    today = date(2026, 7, 16)
    days = {today - timedelta(days=1), today - timedelta(days=2)}
    assert streak_days(days, today) == 2


def test_streak_gap_and_empty():
    today = date(2026, 7, 16)
    assert streak_days({today, today - timedelta(days=2)}, today) == 1
    assert streak_days(set(), today) == 0
