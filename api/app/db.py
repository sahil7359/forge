"""Async engine + per-request RLS context (Schema.md §2).

Every request runs inside one transaction whose first statement is
set_config('app.user_id', <uuid>, true) — RLS scopes all SQL to that user.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(
            url,
            connect_args={"statement_cache_size": 0},  # Supabase session pooler (TechSpec §1)
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
        )
    return _engine


async def get_conn(request: Request) -> AsyncIterator[AsyncConnection]:
    """Transaction-per-request with RLS user context; requires an auth dependency
    to have set request.state.user_id first."""
    async with engine().begin() as conn:
        await conn.execute(
            text("select set_config('app.user_id', :uid, true)"),
            {"uid": str(request.state.user_id)},
        )
        yield conn
