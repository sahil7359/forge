"""Rate limits (TechSpec §3): 60 req/min per token (per IP when unauthenticated) and
10/min per IP for 401s. In-memory sliding windows — single Render instance by design;
swap for a shared store before ever scaling out.

slowapi was specified but its middleware cannot enforce default limits (Starlette
middlewares run before routing, so it never resolves the endpoint); this native
implementation is smaller and covered by tests/test_auth_and_limits.py.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

REQUESTS_PER_MIN = 60
UNAUTH_LIMIT = 10  # 401s per IP per window
WINDOW_S = 60
EXEMPT_PATHS = {"/healthz"}  # Render's own probes must never be throttled

_requests: dict[str, deque[float]] = defaultdict(deque)
_failures: dict[str, deque[float]] = defaultdict(deque)


def _key(request: Request) -> str:
    token = request.headers.get("authorization", "")
    if token:
        return "t:" + hashlib.sha256(token.encode()).hexdigest()[:16]
    return "ip:" + (request.client.host if request.client else "unknown")


def _slide(window: deque[float], now: float) -> None:
    while window and now - window[0] > WINDOW_S:
        window.popleft()


def _429(message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": "rate_limited", "message": message}}, status_code=429)


class RateLimit(BaseHTTPMiddleware):
    """Sliding-window per token/IP + failed-auth burnout per IP (slows token guessing)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        now = time.monotonic()
        ip = request.client.host if request.client else "unknown"

        fails = _failures[ip]
        _slide(fails, now)
        if len(fails) >= UNAUTH_LIMIT:
            return _429("too many failed auth attempts")

        window = _requests[_key(request)]
        _slide(window, now)
        if len(window) >= REQUESTS_PER_MIN:
            return _429("request rate exceeded")
        window.append(now)

        response = await call_next(request)
        if response.status_code == 401:
            fails.append(now)
        return response


def reset() -> None:
    """Test hook — clear all windows."""
    _requests.clear()
    _failures.clear()
