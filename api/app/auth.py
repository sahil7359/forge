"""Bearer auth, two static tokens with scopes (TechSpec §3, Security.md §3).

TODO P2:
- FastAPI dependencies `require_user` / `require_agent`: parse Authorization header,
  hmac.compare_digest against settings tokens, 401 unknown / 403 wrong scope.
- On success: resolve user_id (v1: the single seed user) and stash on request.state.
- DB session dependency calls set_config('app.user_id', ...) per request (db.py).
- v2 swap point: replace user-token branch with Supabase Auth JWT verification only —
  keep this module the single auth boundary.
"""
