"""Midnight report job — 00:05 IST (AppFlow Flow 5). Retry once at 07:00 if failed.

TODO P4:
1. Pull yesterday's full context (logs, tasks closed/open, expenses, streak, day counter).
2. llm report (temp 0.4) with fixed sections: shipped / blockers / numbers / streak & gates /
   tomorrow's plan (<=3) / one hard truth.
3. api_post('/v1/reports', {date, kind:'daily', md, stats, model})
4. push 'Day N report ready' to all subs; api_post('/v1/nudges', kind='report_ready').

Run: python -m forge_agent.report
"""

if __name__ == "__main__":
    raise SystemExit("TODO P4: implement per docstring")
