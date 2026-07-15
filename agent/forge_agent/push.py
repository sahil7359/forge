"""Web Push sender (VAPID). Shared by nudge/report/archive jobs and Actions fallbacks."""

import json

from pywebpush import WebPushException, webpush

from forge_agent.config import settings


def send(sub: dict, title: str, body: str) -> bool:
    """sub = {endpoint, p256dh, auth}. Returns False on a dead (404/410) subscription."""
    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps({"title": title[:40], "body": body[:220]}),  # caps: Security.md §6
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            return False  # caller reports failure -> API prunes after 3 (AppFlow Flow 9)
        raise
