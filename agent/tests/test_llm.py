"""LLM output contract: JSON validation, retry-then-template, skip-on-down (TechSpec §5-6)."""

from __future__ import annotations

import pytest
from forge_agent import llm
from pydantic import ValidationError


def test_parse_valid_json():
    p = llm._parse_nudge('{"title": "Day 2/84", "body": "Next: tests. One line."}')
    assert p.title == "Day 2/84"


def test_parse_code_fenced_json():
    p = llm._parse_nudge('```json\n{"title": "t", "body": "b"}\n```')
    assert (p.title, p.body) == ("t", "b")


def test_parse_json_with_prose_around():
    p = llm._parse_nudge('Sure! {"title": "t", "body": "b"} hope that helps')
    assert p.title == "t"


@pytest.mark.parametrize(
    "bad",
    [
        "no json at all",
        '{"title": "only title"}',
        '{"title": "' + "x" * 41 + '", "body": "b"}',  # 41-char title
        '{"title": "t", "body": "' + "y" * 221 + '"}',  # 221-char body
        '{"title": "", "body": "b"}',
    ],
)
def test_parse_rejects_invalid(bad):
    with pytest.raises((ValueError, ValidationError)):
        llm._parse_nudge(bad)


def test_retry_once_then_success(monkeypatch):
    calls = []

    def fake_chat(system, user, temperature, num_predict):
        calls.append(user)
        if len(calls) == 1:
            return "garbage output", 100
        return '{"title": "t", "body": "b"}', 120

    monkeypatch.setattr(llm, "_chat", fake_chat)
    payload, latency = llm.nudge("sys", "usr")
    assert payload.title == "t"
    assert latency == 220  # both calls counted
    assert len(calls) == 2
    assert llm.RETRY_REMINDER in calls[1]


def test_two_failures_raise_fallback(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: ("not json", 50))
    with pytest.raises(llm.LLMFallback):
        llm.nudge("sys", "usr")


def test_ollama_down_raises_unavailable(monkeypatch):
    monkeypatch.setattr(llm.httpx, "post", _raise_connect)
    with pytest.raises(llm.LLMUnavailable):
        llm._chat("s", "u", 0.6, 120)


def _raise_connect(*a, **k):
    import httpx

    raise httpx.ConnectError("connection refused")


def test_report_strips_html_and_caps(monkeypatch):
    monkeypatch.setattr(
        llm, "_chat", lambda *a, **k: ("## Shipped\n<script>alert(1)</script>done", 10)
    )
    md, _ = llm.report_md("s", "u")
    assert "<script>" not in md
    assert "done" in md


def test_template_nudge_respects_caps(ctx):
    p = llm.template_nudge(ctx)
    assert len(p.title) <= 40
    assert len(p.body) <= 220
    assert "write token validation tests" in p.body


def test_template_nudge_empty_context():
    p = llm.template_nudge({})
    assert p.title and p.body
    assert len(p.title) <= 40
