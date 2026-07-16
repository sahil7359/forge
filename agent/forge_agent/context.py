"""Prompt builders: /v1/context bundle -> (system, user) message pair.

The system prompts live in agent/prompts/*.txt and are hand-written by Sahil
(Rules R1) — this module only assembles context around them. User log text is
untrusted and always fenced inside <logs>…</logs> (Security §6); snapshot tests
in tests/test_prompts.py guard against silent regressions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


def _system(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def _fence(entries: list[str]) -> str:
    # neutralize any attempt to close the fence from inside user text
    safe = [e.replace("</logs", "<\\/logs") for e in entries]
    return "<logs>\n" + "\n".join(safe) + "\n</logs>"


def _log_line(log: dict[str, Any]) -> str:
    ts = str(log.get("ts", ""))[11:16]  # HH:MM — logs are already IST in the bundle
    return f"{ts} {log.get('type', 'checkin')}: {log.get('text', '')}"


def build_nudge_prompt(ctx: dict[str, Any]) -> tuple[str, str]:
    slim = {
        "now_ist": ctx.get("now_ist"),
        "day_counter": ctx.get("day_counter"),
        "day_total": ctx.get("day_total"),
        "streak": ctx.get("streak"),
        "last_log_min_ago": ctx.get("last_log_min_ago"),
        "escalation": ctx.get("escalation"),
        "deep_work": ctx.get("deep_work"),
        "pending_tasks": ctx.get("pending_tasks", []),
        "yesterday_plan": ctx.get("yesterday_plan", []),
        "last_nudges": ctx.get("last_nudges", []),
        "expenses_today": ctx.get("expenses_today"),
    }
    user = (
        "CONTEXT JSON:\n"
        + json.dumps(slim, ensure_ascii=False)
        + "\n"
        + _fence([_log_line(entry) for entry in ctx.get("todays_logs", [])])
        + "\nReturn the nudge JSON now."
    )
    return _system("nudge_system.txt"), user


def build_report_prompt(day: str, data: dict[str, Any], stats: dict[str, Any]) -> tuple[str, str]:
    slim = {
        "date": day,
        "day_counter": data.get("day_counter"),
        "day_total": data.get("day_total"),
        "streak": data.get("streak"),
        "stats": stats,
        "pending_tasks": data.get("pending_tasks", []),
    }
    user = (
        "CONTEXT JSON:\n"
        + json.dumps(slim, ensure_ascii=False)
        + "\n"
        + _fence([_log_line(entry) for entry in data.get("logs", [])])
        + "\nWrite the daily report markdown now."
    )
    return _system("report_system.txt"), user
