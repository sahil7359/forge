"""Hourly nudge job — Task Scheduler :00, 07:00-22:00 IST (AppFlow Flow 3).

TODO P4 (order matters):
1. ctx = api_get('/v1/context')            # server computed escalation + deep_work
2. Re-check suppression client-side (defense in depth; same rules as server —
   window / last_log<25min / last_nudge<50min / deep-work active).
3. If ctx['escalation'] == 0 and nothing pending and last hour had a nudge -> exit quiet.
4. prompt = build_prompt('prompts/nudge_system.txt', ctx)   # snapshot-tested
5. payload = llm.nudge(prompt)             # or deterministic template on LLMFallback
6. subs = api_get('/v1/push/subscriptions')
7. ok per sub -> push.send(...); report dead subs.
8. api_post('/v1/nudges', {...kind:'hourly', escalation, model, latency_ms})  # audit

Run: python -m forge_agent.nudge
"""

if __name__ == "__main__":
    raise SystemExit("TODO P4: implement per docstring")
