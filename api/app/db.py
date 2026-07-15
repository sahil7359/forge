"""Async engine + per-request RLS context (Schema.md §2).

TODO P2:
- create_async_engine(settings.database_url.replace('postgresql://','postgresql+asyncpg://'),
  connect_args={'statement_cache_size': 0})   # Supabase pooler requirement (TechSpec §1)
- async_sessionmaker; dependency yielding a session that first executes
  select set_config('app.user_id', :uid, true)  — RLS enforces per-user isolation.
- No ORM models beyond thin table metadata; plain SQL via text() is fine (Rules.md R4).
"""
