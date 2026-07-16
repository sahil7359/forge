"""Ollama client + output contract (TechSpec §5-6).

Failure semantics (deliberate, TechSpec §6):
- Ollama unreachable / timeout      -> LLMUnavailable  (caller SKIPS — Actions fallback covers)
- Output invalid after one retry    -> LLMFallback     (caller uses deterministic template)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from forge_agent.config import settings


class LLMUnavailable(Exception):
    pass


class LLMFallback(Exception):
    pass


class NudgePayload(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    body: str = Field(min_length=1, max_length=220)


RETRY_REMINDER = (
    "Your previous output was invalid. Return ONLY the JSON object "
    '{"title": "<= 40 chars", "body": "<= 220 chars"} — no prose, no code fences.'
)
REPORT_MAX_CHARS = 8000
_TAG = re.compile(r"<[^>]+>")


def _chat(system: str, user: str, temperature: float, num_predict: int) -> tuple[str, int]:
    """Returns (text, latency_ms). Raises LLMUnavailable on transport problems."""
    started = time.perf_counter()
    try:
        r = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"temperature": temperature, "num_predict": num_predict},
                "stream": False,
            },
            timeout=settings.ollama_timeout_s,
        )
        r.raise_for_status()
    except (httpx.HTTPError, OSError) as e:
        raise LLMUnavailable(str(e)) from e
    latency_ms = int((time.perf_counter() - started) * 1000)
    return r.json()["message"]["content"].strip(), latency_ms


def _parse_nudge(text: str) -> NudgePayload:
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    obj = json.loads(text[start : end + 1])
    return NudgePayload(**obj)


def nudge(system: str, user: str) -> tuple[NudgePayload, int]:
    """One retry on invalid output, then LLMFallback (TechSpec §5)."""
    text, latency = _chat(system, user, temperature=0.6, num_predict=120)
    try:
        return _parse_nudge(text), latency
    except (ValueError, ValidationError, json.JSONDecodeError):
        pass
    text, retry_latency = _chat(system, user + "\n" + RETRY_REMINDER, 0.6, 120)
    try:
        return _parse_nudge(text), latency + retry_latency
    except (ValueError, ValidationError, json.JSONDecodeError) as e:
        raise LLMFallback(f"invalid nudge output after retry: {e}") from e


def report_md(system: str, user: str) -> tuple[str, int]:
    """Markdown out; HTML stripped before it ever reaches storage (Security §6)."""
    text, latency = _chat(system, user, temperature=0.4, num_predict=900)
    md = _TAG.sub("", text)[:REPORT_MAX_CHARS].strip()
    if not md:
        raise LLMFallback("empty report output")
    return md, latency


def template_nudge(ctx: dict[str, Any]) -> NudgePayload:
    """Deterministic fallback — mechanical, no coach voice (that's the LLM's job)."""
    day = ctx.get("day_counter")
    title = f"Day {day}/{ctx.get('day_total', 84)} · check-in" if day else "Forge · check-in"
    pending = ctx.get("pending_tasks") or []
    plan = ctx.get("yesterday_plan") or []
    ask = (pending[0].get("title") if pending else None) or (plan[0] if plan else None)
    minutes = ctx.get("last_log_min_ago")
    quiet = f"{minutes} min quiet. " if minutes is not None else ""
    body = f"{quiet}Next: {ask}. One line back." if ask else f"{quiet}What moved? One line back."
    return NudgePayload(title=title[:40], body=body[:220])
