"""Forge API — FastAPI wiring: middlewares, error shape, routers (TechSpec §3)."""

from __future__ import annotations

import time

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.ratelimit import RateLimit
from app.routes import agent, logs, push, reports, tasks
from app.routes import settings as settings_routes

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()

BODY_CAP = 32 * 1024
ARCHIVE_BODY_CAP = 8 * 1024 * 1024  # monthly raw archives are MBs by design (Schema §6)

_STATUS_CODES = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal",
}


def _error(status: int, message: str, code: str | None = None) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code or _STATUS_CODES.get(status, "error"), "message": message}},
        status_code=status,
    )


class BodyCap(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cap = ARCHIVE_BODY_CAP if request.url.path == "/v1/archives/monthly" else BODY_CAP
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > cap:
            return _error(413, "request body too large")
        return await call_next(request)


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path != "/healthz":
            log.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=round((time.perf_counter() - started) * 1000, 1),
            )
        return response


app = FastAPI(title="forge-api", docs_url=None, redoc_url=None, openapi_url=None)

app.include_router(logs.router, prefix="/v1")
app.include_router(tasks.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(push.router, prefix="/v1")
app.include_router(settings_routes.router, prefix="/v1")
app.include_router(agent.router, prefix="/v1")

# added last = outermost; CORS must wrap everything so error responses carry headers too
app.add_middleware(RateLimit)
app.add_middleware(BodyCap)
app.add_middleware(SecurityHeaders)
if settings.cors_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],  # exact allowlist — never widen (Security.md §4)
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return _error(exc.status_code, exc.detail.get("message", ""), exc.detail.get("code"))
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exc(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(422, str(exc.errors())[:500])


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}  # leaks nothing (Security.md §4)
