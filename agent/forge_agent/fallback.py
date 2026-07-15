"""GitHub Actions entrypoints (AppFlow Flow 7) — LLM-free by design.

Usage: python -m forge_agent.fallback {nudge|report}

TODO P5:
- nudge:  ctx = api_get('/v1/context'); exit 0 quietly if a nudge OR log exists in last
  70 min or outside window; else template push ('No coach this hour — Rig 2 looks offline.
  What moved since {last_log}? One line.') + api_post('/v1/nudges', kind='fallback').
- report: if yesterday(IST) has no report -> compute stats-only md from /v1/logs,
  api_post('/v1/reports', kind='daily_fallback') + push. On the 1st: also verify last
  month's archive row exists, else alert push (archive check).
"""

if __name__ == "__main__":
    raise SystemExit("TODO P5: implement per docstring")
