"""Hourly nudge job — Task Scheduler :00, 07:00-22:00 IST (AppFlow Flow 3).

Run: python -m forge_agent.nudge
Exit 0 always unless the API itself is unreachable — a silent hour is a decision,
not a failure; the Actions fallback covers real outages.
"""

from __future__ import annotations

import sys
from datetime import datetime

import structlog

from forge_agent import context, llm, push, rules
from forge_agent.http import api_get, api_post

log = structlog.get_logger()


def send_to_all(title: str, body: str) -> int:
    """Push to every live subscription; report dead ones so the API prunes them."""
    subs = api_get("/v1/push/subscriptions")["subscriptions"]
    sent = 0
    for sub in subs:
        if push.send(sub, title, body):
            sent += 1
        else:
            api_post(f"/v1/push/subscriptions/{sub['id']}/failure", {})
            log.warning("dead_subscription", id=sub["id"])
    return sent


def main() -> int:
    ctx = api_get("/v1/context")
    hour = datetime.fromisoformat(ctx["now_ist"]).hour

    reason = rules.suppress(ctx, hour)
    if reason:
        log.info("suppressed", reason=reason)
        return 0
    if rules.quiet_hour(ctx):
        log.info("suppressed", reason="quiet_hour")
        return 0

    system, user = context.build_nudge_prompt(ctx)
    model = None
    latency = None
    try:
        payload, latency = llm.nudge(system, user)
        from forge_agent.config import settings

        model = settings.model
    except llm.LLMUnavailable as e:
        log.warning("ollama_down_skip", error=str(e))  # Actions fallback covers this hour
        return 0
    except llm.LLMFallback as e:
        log.warning("template_fallback", error=str(e))
        payload = llm.template_nudge(ctx)

    sent = send_to_all(payload.title, payload.body)
    api_post(
        "/v1/nudges",
        {
            "kind": "hourly",
            "title": payload.title,
            "body": payload.body,
            "escalation": ctx.get("escalation", 0),
            "model": model,
            "latency_ms": latency,
        },
    )
    log.info("nudge_sent", sent=sent, escalation=ctx.get("escalation"), latency_ms=latency)
    return 0


if __name__ == "__main__":
    sys.exit(main())
