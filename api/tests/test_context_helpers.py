"""parse_tomorrow_plan — yesterday's plan drives the morning nudge (AppFlow Flow 3)."""

from __future__ import annotations

from app.routes.agent import parse_tomorrow_plan

MD = """## Shipped today
- auth middleware

## Tomorrow's plan
- finish token validation tests
- deploy API to staging
- 30 min workout
- overflow item never included

## One hard truth
Stop rereading docs.
"""


def test_extracts_max_three_bullets():
    assert parse_tomorrow_plan(MD) == [
        "finish token validation tests",
        "deploy API to staging",
        "30 min workout",
    ]


def test_numbered_lists_work():
    md = "## Tomorrow's plan\n1. first\n2. second\n"
    assert parse_tomorrow_plan(md) == ["first", "second"]


def test_missing_section_or_report():
    assert parse_tomorrow_plan("## Shipped today\n- x\n") == []
    assert parse_tomorrow_plan(None) == []
    assert parse_tomorrow_plan("") == []
