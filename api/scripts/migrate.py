"""Apply migrations/*.sql in order, tracked in schema_migrations.

Run with the postgres superuser URL once (Supabase SQL editor also works for 000 manual roles):
    DATABASE_URL=postgresql://postgres:...  python scripts/migrate.py
"""

import asyncio
import os
import pathlib

import asyncpg


def load_migrations() -> list[tuple[str, str]]:
    mig_dir = pathlib.Path(__file__).resolve().parents[1] / "migrations"
    return [(f.name, f.read_text()) for f in sorted(mig_dir.glob("*.sql"))]


async def main() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(
        "create table if not exists schema_migrations"
        "(name text primary key, applied_at timestamptz not null default now())"
    )
    for name, sql in load_migrations():
        if await conn.fetchval("select 1 from schema_migrations where name=$1", name):
            continue
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute("insert into schema_migrations(name) values($1)", name)
        print("applied", name)
    await conn.close()


asyncio.run(main())
