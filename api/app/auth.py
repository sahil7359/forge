"""Bearer auth: two static tokens with scopes (TechSpec §3, Security.md §3).

v2 swap point: replace the user-token branch with Supabase Auth JWT verification —
keep this module the single auth boundary.
"""

from __future__ import annotations

import hmac
import uuid

from fastapi import HTTPException, Request
from sqlalchemy import text

from app.config import settings

_seed_user_id: uuid.UUID | None = None


def _token_from(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "missing bearer token")
    return token.strip()


def _scope_of(token: str) -> str:
    if settings.user_token and hmac.compare_digest(token, settings.user_token):
        return "user"
    if settings.agent_token and hmac.compare_digest(token, settings.agent_token):
        return "agent"
    raise HTTPException(401, "unknown token")


async def resolve_user_id() -> uuid.UUID:
    """v1: the single seed user (needs migrations/004_users_lookup.sql)."""
    global _seed_user_id
    if _seed_user_id is None:
        from app.db import engine  # deferred: tests stub this cache without a DB

        async with engine().connect() as conn:
            row = await conn.execute(text("select id from users order by created_at limit 1"))
            found = row.scalar()
        if found is None:
            raise HTTPException(500, "no seed user (run migration 003)")
        _seed_user_id = found
    return _seed_user_id


async def _require(request: Request, scope: str) -> None:
    actual = _scope_of(_token_from(request))
    if actual != scope:
        raise HTTPException(403, f"requires {scope} scope")
    request.state.user_id = await resolve_user_id()
    request.state.scope = actual


async def require_user(request: Request) -> None:
    await _require(request, "user")


async def require_agent(request: Request) -> None:
    await _require(request, "agent")
