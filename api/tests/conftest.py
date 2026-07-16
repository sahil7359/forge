"""Shared fixtures: token config, seed-user stub, fake DB conn, rate-limit reset.

CI has no Postgres — routes are exercised through dependency overrides; the SQL
integration surface is covered by the deployed-curl walkthrough (P2 DoD).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app import auth, ratelimit
from app.config import settings
from app.db import get_conn
from app.main import app
from fastapi.testclient import TestClient

USER_TOKEN = "test-user-token-0000000000000000"
AGENT_TOKEN = "test-agent-token-000000000000000"


class FakeResult:
    def __init__(self, rows: list[Any] | None = None, scalar: Any = None):
        self.rows = rows or []
        self._scalar = scalar

    def __iter__(self):
        return iter(self.rows)

    def scalar(self):
        return self._scalar

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


class FakeConn:
    """Returns queued FakeResults in order; empty default for everything else."""

    def __init__(self, queue: list[FakeResult] | None = None):
        self.queue = list(queue or [])
        self.statements: list[str] = []

    async def execute(self, statement, params=None):
        self.statements.append(str(statement))
        return self.queue.pop(0) if self.queue else FakeResult()


@pytest.fixture(autouse=True)
def _tokens_and_clean_state():
    settings.user_token = USER_TOKEN
    settings.agent_token = AGENT_TOKEN
    auth._seed_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    ratelimit.reset()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    def fake_conn():
        yield FakeConn()

    app.dependency_overrides[get_conn] = fake_conn
    return TestClient(app)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
