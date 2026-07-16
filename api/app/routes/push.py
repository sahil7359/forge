"""Push subscriptions: user manages own; agent lists live ones to send (TechSpec §3)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import require_agent, require_user
from app.db import get_conn
from app.schemas import SubscriptionIn

router = APIRouter()

DEAD_AFTER_FAILURES = 3


@router.post("/push/subscriptions", status_code=201, dependencies=[Depends(require_user)])
async def subscribe(
    body: SubscriptionIn, request: Request, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    row = (
        await conn.execute(
            text(
                "insert into push_subscriptions (user_id, endpoint, p256dh, auth, ua)"
                " values (:uid, :endpoint, :p256dh, :auth, :ua)"
                " on conflict (endpoint) do update set p256dh = excluded.p256dh,"
                "   auth = excluded.auth, ua = excluded.ua, failures = 0"
                " returning id"
            ),
            {
                "uid": str(request.state.user_id),
                "endpoint": body.endpoint,
                "p256dh": body.p256dh,
                "auth": body.auth,
                "ua": body.ua,
            },
        )
    ).one()
    return {"id": str(row.id)}


@router.delete(
    "/push/subscriptions/{sub_id}", status_code=204, dependencies=[Depends(require_user)]
)
async def unsubscribe(sub_id: uuid.UUID, conn: AsyncConnection = Depends(get_conn)) -> None:
    gone = (
        await conn.execute(
            text("delete from push_subscriptions where id = :id returning id"),
            {"id": str(sub_id)},
        )
    ).scalar()
    if gone is None:
        raise HTTPException(404, {"code": "not_found", "message": "subscription not found"})


@router.post("/push/subscriptions/{sub_id}/failure", dependencies=[Depends(require_agent)])
async def report_failure(
    sub_id: uuid.UUID, conn: AsyncConnection = Depends(get_conn)
) -> dict[str, Any]:
    """Senders report 404/410 pushes; after 3 failures the subscription drops out of
    the live list (AppFlow Flow 9). A later successful subscribe resets the counter."""
    row = (
        await conn.execute(
            text(
                "update push_subscriptions set failures = failures + 1"
                " where id = :id returning failures"
            ),
            {"id": str(sub_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "subscription not found"})
    return {
        "id": str(sub_id),
        "failures": row.failures,
        "dead": row.failures >= DEAD_AFTER_FAILURES,
    }


@router.get("/push/subscriptions", dependencies=[Depends(require_agent)])
async def list_live(conn: AsyncConnection = Depends(get_conn)) -> dict[str, Any]:
    rows = await conn.execute(
        text(
            "select id, endpoint, p256dh, auth from push_subscriptions"
            " where failures < :dead order by created_ts"
        ),
        {"dead": DEAD_AFTER_FAILURES},
    )
    return {
        "subscriptions": [
            {"id": str(r.id), "endpoint": r.endpoint, "p256dh": r.p256dh, "auth": r.auth}
            for r in rows
        ]
    }
