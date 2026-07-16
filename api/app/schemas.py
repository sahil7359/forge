"""Pydantic v2 boundary models (TechSpec §3). Everything user-supplied is length-capped;
LLM-produced fields get looser caps here — the agent enforces the 40/220 push caps."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.time import now_ist

LogType = Literal["checkin", "task", "expense", "fitness", "habit"]

CLIENT_TS_MAX_PAST = timedelta(days=7)
CLIENT_TS_MAX_SKEW = timedelta(minutes=5)


class LogIn(BaseModel):
    id: uuid.UUID  # client-generated (offline idempotency, AppFlow Flow 2)
    type: LogType = "checkin"
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    data: dict[str, Any] = Field(default_factory=dict)
    ts: datetime | None = None  # optional client time for offline replay, bounded below

    @field_validator("ts")
    @classmethod
    def _sane_ts(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            raise ValueError("ts must be timezone-aware")
        now = now_ist()
        if v > now + CLIENT_TS_MAX_SKEW or v < now - CLIENT_TS_MAX_PAST:
            raise ValueError("ts outside accepted replay window")
        return v

    @field_validator("data")
    @classmethod
    def _known_keys_typed(cls, v: dict[str, Any]) -> dict[str, Any]:
        # Schema.md §3: unknown keys allowed; known keys must be sane.
        for key in ("amount", "block_minutes", "duration_min"):
            if key in v and not isinstance(v[key], int | float):
                raise ValueError(f"data.{key} must be a number")
        if "amount" in v and not 0 <= float(v["amount"]) <= 10_000_000:
            raise ValueError("data.amount out of range")
        if "block_minutes" in v and not 0 < float(v["block_minutes"]) <= 480:
            raise ValueError("data.block_minutes out of range")
        return v


class TaskIn(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=300)]
    origin_log_id: uuid.UUID | None = None


class TaskPatch(BaseModel):
    status: Literal["pending", "done", "dropped"]


class SubscriptionIn(BaseModel):
    endpoint: Annotated[str, Field(min_length=1, max_length=2000)]
    p256dh: Annotated[str, Field(min_length=1, max_length=300)]
    auth: Annotated[str, Field(min_length=1, max_length=100)]
    ua: Annotated[str | None, Field(max_length=300)] = None


class NudgeIn(BaseModel):
    kind: Literal["hourly", "fallback", "report_ready"]
    title: Annotated[str, Field(min_length=1, max_length=80)]
    body: Annotated[str, Field(min_length=1, max_length=400)]
    escalation: Annotated[int, Field(ge=0, le=3)] = 0
    model: Annotated[str | None, Field(max_length=80)] = None
    latency_ms: Annotated[int | None, Field(ge=0)] = None


class ReportIn(BaseModel):
    date: date
    kind: Literal["daily", "daily_fallback"]
    md: Annotated[str, Field(min_length=1, max_length=30_000)]
    stats: dict[str, Any] = Field(default_factory=dict)
    model: Annotated[str | None, Field(max_length=80)] = None


class ArchiveIn(BaseModel):
    ym: Annotated[str, Field(pattern=r"^\d{4}-\d{2}$")]
    md: Annotated[str, Field(min_length=1, max_length=200_000)]
    raw: dict[str, Any]  # verbatim {logs[], nudges[], reports[]} incl. every timestamp
    stats: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, int]

    @field_validator("counts")
    @classmethod
    def _complete_counts(cls, v: dict[str, int]) -> dict[str, int]:
        missing = {"logs", "nudges", "reports"} - v.keys()
        if missing:
            raise ValueError(f"counts missing {sorted(missing)}")
        if any(n < 0 for n in v.values()):
            raise ValueError("counts must be >= 0")
        return v


class PurgeIn(BaseModel):
    ym: Annotated[str, Field(pattern=r"^\d{4}-\d{2}$")]
