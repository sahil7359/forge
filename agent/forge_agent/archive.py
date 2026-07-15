"""Month-close job — 1st, 00:25 IST (AppFlow Flow 6; Schema.md §4-5 is the law).

TODO P4:
1. ym = prev month; pull ALL logs/nudges/reports in ym window (paginated).
2. Build md (month report) + raw jsonb (verbatim rows, every timestamp) + stats + counts.
3. api_post('/v1/archives/monthly', ...)   -> server verifies + stores
4. api_post('/v1/purge', {'ym': ym})       -> server enforces verify-before-delete invariant
5. Push confirmation ('June archived: N logs') or the 409 alert.
NEVER implement deletion client-side; the invariant lives in the API only.

Run: python -m forge_agent.archive
"""

if __name__ == "__main__":
    raise SystemExit("TODO P4: implement per docstring")
