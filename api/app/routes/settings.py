"""GET/PATCH /settings — Design §5 Settings screen persistence.

Not in the original TechSpec §3 table; added in P3 because the nudge window/gap/
threshold live server-side (the agent reads them from the settings table).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_user
from app.db import get_conn
from app.schemas import SettingsPatch

router = APIRouter(dependencies=[Depends(require_user)])

FIELDS = (
    "active_start",
    "active_end",
    "nudge_min_gap_min",
    "suppress_after_log_min",
    "hard_mode_after_hours",
)


def _out(row: Any) -> dict[str, Any]:
    return {
        **{f: getattr(row, f) for f in FIELDS},
        "plan_day_anchor": row.plan_day_anchor.isoformat() if row.plan_day_anchor else None,
    }


@router.get("/settings")
async def get_settings(conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    row = (
        await conn.execute(text(f"select {', '.join(FIELDS)}, plan_day_anchor from settings"))
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "no settings row (seed 003)"})
    return _out(row)


@router.patch("/settings")
async def patch_settings(
    body: SettingsPatch, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, {"code": "validation_error", "message": "no fields to update"})
    sets = ", ".join(f"{k} = :{k}" for k in changes)
    row = (
        await conn.execute(
            text(
                f"update settings set {sets}, updated_at = now()"
                f" returning {', '.join(FIELDS)}, plan_day_anchor"
            ),
            changes,
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "no settings row (seed 003)"})
    return _out(row)
