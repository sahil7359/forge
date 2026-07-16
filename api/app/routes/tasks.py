"""POST /tasks · GET /tasks · PATCH /tasks/{id} (TechSpec §3)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_user
from app.db import get_conn
from app.schemas import TaskIn, TaskPatch

router = APIRouter(dependencies=[Depends(require_user)])


def _out(r: Any) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "title": r.title,
        "status": r.status,
        "created_ts": r.created_ts.isoformat(),
        "closed_ts": r.closed_ts.isoformat() if r.closed_ts else None,
    }


@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "insert into tasks (user_id, title, origin_log_id) values (:uid, :title, :olid)"
                " returning id, title, status, created_ts, closed_ts"
            ),
            {
                "uid": str(request.state.user_id),
                "title": body.title,
                "olid": str(body.origin_log_id) if body.origin_log_id else None,
            },
        )
    ).one()
    return _out(row)


@router.get("/tasks")
async def list_tasks(
    status: str = "pending", conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    if status not in ("pending", "done", "dropped"):
        raise HTTPException(422, {"code": "validation_error", "message": "bad status"})
    rows = await conn.execute(
        text(
            "select id, title, status, created_ts, closed_ts from tasks"
            " where status = :st order by created_ts"
        ),
        {"st": status},
    )
    return {"tasks": [_out(r) for r in rows]}


@router.patch("/tasks/{task_id}")
async def patch_task(
    task_id: uuid.UUID, body: TaskPatch, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "update tasks set status = :st,"
                " closed_ts = case when :st = 'pending' then null else now() end"
                " where id = :id"
                " returning id, title, status, created_ts, closed_ts"
            ),
            {"st": body.status, "id": str(task_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "task not found"})
    return _out(row)
