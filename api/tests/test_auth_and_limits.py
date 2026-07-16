"""Auth/scope matrix + quota/rate-limit 429s + body cap (Rules R5, TechSpec §3)."""

from __future__ import annotations

import uuid

import pytest
from app.db import get_conn
from app.main import app
from conftest import AGENT_TOKEN, USER_TOKEN, FakeConn, FakeResult, auth_header
from fastapi.testclient import TestClient

USER_ROUTES = [("GET", "/v1/tasks"), ("GET", "/v1/today"), ("GET", "/v1/archives")]
AGENT_ROUTES = [("GET", "/v1/context"), ("GET", "/v1/push/subscriptions")]


@pytest.mark.parametrize(("method", "path"), USER_ROUTES + AGENT_ROUTES)
def test_no_token_is_401(client, method, path):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), USER_ROUTES + AGENT_ROUTES)
def test_garbage_token_is_401(client, method, path):
    r = client.request(method, path, headers=auth_header("nope-" + "x" * 30))
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(("method", "path"), AGENT_ROUTES)
def test_user_token_on_agent_route_is_403(client, method, path):
    assert client.request(method, path, headers=auth_header(USER_TOKEN)).status_code == 403


@pytest.mark.parametrize(("method", "path"), USER_ROUTES)
def test_agent_token_on_user_route_is_403(client, method, path):
    assert client.request(method, path, headers=auth_header(AGENT_TOKEN)).status_code == 403


@pytest.mark.parametrize(
    ("method", "path", "token"),
    [
        ("GET", "/v1/tasks", USER_TOKEN),
        ("GET", "/v1/today", USER_TOKEN),
        ("GET", "/v1/context", AGENT_TOKEN),
        ("GET", "/v1/push/subscriptions", AGENT_TOKEN),
    ],
)
def test_right_scope_is_200(client, method, path, token):
    assert client.request(method, path, headers=auth_header(token)).status_code == 200


def test_healthz_needs_no_auth(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_log_quota_429():
    def full_day_conn():
        yield FakeConn([FakeResult(scalar=500)])  # first query = today's count

    app.dependency_overrides[get_conn] = full_day_conn
    client = TestClient(app)
    body = {"id": str(uuid.uuid4()), "text": "one more"}
    r = client.post("/v1/logs", json=body, headers=auth_header(USER_TOKEN))
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "quota_exceeded"


def test_purge_without_archive_is_409_archive_missing():
    def no_archive_conn():
        yield FakeConn([FakeResult(scalar=None)])  # archive_counts -> None

    app.dependency_overrides[get_conn] = no_archive_conn
    client = TestClient(app)
    r = client.post("/v1/purge", json={"ym": "2026-06"}, headers=auth_header(AGENT_TOKEN))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "archive_missing"


def test_body_cap_413(client):
    r = client.post("/v1/logs", content=b"x" * (32 * 1024 + 1), headers=auth_header(USER_TOKEN))
    assert r.status_code == 413


def test_unauth_ip_burns_out_at_10_failures(client):
    for _ in range(10):
        assert client.get("/v1/tasks", headers=auth_header("bad" + "x" * 30)).status_code == 401
    r = client.get("/v1/tasks", headers=auth_header("bad" + "x" * 30))
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_token_rate_limit_60_per_minute(client):
    codes = [
        client.get("/v1/tasks", headers=auth_header(USER_TOKEN)).status_code for _ in range(61)
    ]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429


def test_security_headers_present(client):
    r = client.get("/healthz")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
