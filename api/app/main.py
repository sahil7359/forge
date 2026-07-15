from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="forge-api", docs_url=None, redoc_url=None, openapi_url=None)

if settings.cors_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],  # exact allowlist — never widen (Security.md §4)
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}  # leaks nothing (Security.md §4)


# TODO P2 (TechSpec §3): routers — logs, tasks, reports, archives, push, context, nudges, purge.
# TODO P2: slowapi limiter (60/min/token; 10/min/IP on 401s), body-size cap middleware,
#          security headers middleware (nosniff, frame-deny, no-referrer).
