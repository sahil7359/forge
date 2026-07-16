# ImplementationPlan — Forge v1

Total budget: **≤ 16 h** (PRD success metric). Phases are sized as single focused build
sessions — one phase at a time; its DoD is the gate. Update Tracker.md after every
session (Rules.md R7). Overrun → cut from PRD "Should" list, never extend.

## P0 — Accounts, keys, scaffold (1 h)

- [ ] GitHub repo `forge` (private), default branch `main`; enable secret scanning; 2FA on
      GitHub, Render, Supabase (Security §5).
- [ ] Scaffold repo tree per TechSpec §2 (see §Session handoff below).
- [ ] Generate secrets: `python -c "import secrets;print(secrets.token_urlsafe(32))"` ×2
      (USER_TOKEN, AGENT_TOKEN); `python -m py_vapid --gen`.
- [ ] Supabase project (Mumbai/ap-south if offered): run migrations 001–003 (Schema.md);
      create `forge_api`, `forge_backup` roles; grab session-pooler DATABASE_URL.
- [ ] Render: new web service from repo Dockerfile; set env (DATABASE_URL, tokens, CORS origin).
- [ ] GitHub Pages enabled (Actions source); Actions secrets set (AGENT_TOKEN, VAPID_PRIVATE,
      VAPID_SUB=mailto:help.sahil.gob@gmail.com, BACKUP_URL, API_BASE).

DoD: empty FastAPI `/healthz` live on Render; blank page on Pages; `ollama list` shows qwen2.5.

## P1 — POC spikes (2.5 h) → run POC.md S1–S3

DoD: all gates green, numbers logged in Tracker.md. Hard stop if S1 fails.

## P2 — DB + API core (3 h)

- [ ] Migrations applied; seed user + settings (`plan_day_anchor = 2026-07-15`).
- [ ] `auth.py` (two tokens, scopes, constant-time; sets `app.user_id` per request),
      `ratelimit.py` (slowapi), routes per TechSpec §3, structlog.
- [ ] IST day-boundary helpers (`core/time.py`) — the only place "today" is computed.
- [ ] `/context` bundle incl. escalation + deep-work computation (server-side, deterministic).
- [ ] `/purge` with the Schema §5 invariant.
- [ ] pytest: auth/scope matrix · suppression+escalation table-driven cases · purge invariant
      (archive-missing, count-mismatch, happy path) · quota/rate 429s. CI green.

DoD: deployed to Render; `curl` walkthrough of every route passes; tests green in Actions.

## P3 — PWA (3 h)

- [ ] index.html/app.js per Design.md (Today, Reports, Settings; composer + chips; feed).
- [ ] sw.js: push handler + notificationclick (focus app), offline shell cache.
- [ ] IndexedDB queue + replay; client-UUID logs.
- [ ] Subscribe/test-push flow; settings persistence; DOMPurify render path; jsPDF export
      (monthly + yearly compile from archives).
- [ ] Icons + manifest (standalone, theme #0B0E14); deploy via Pages workflow.

DoD: installed on iPhone, logging works offline→sync, test push arrives, report renders, PDF
downloads with timestamp appendix (use a hand-inserted fixture archive row).

## P4 — Agent on Rig 2 (2.5 h)

- [ ] `forge_agent`: context fetch (tenacity), suppression re-check client-side (defense in
      depth), Ollama client (90 s timeout, JSON validate + 1 retry + template fallback),
      pywebpush sender, nudge/report/archive jobs.
- [ ] Prompts: write `nudge_system.txt` + `report_system.txt` **by hand** (Rules R1) — tone:
      adaptive coach, L3 hard mode (names avoidance patterns, blunt language), fenced untrusted
      log block, JSON contract, anti-repetition clause.
- [ ] `register_tasks.ps1`: hourly 07–22 :00, daily 00:05, monthly 1st 00:25; wake-to-run,
      run-if-missed.
- [ ] pytest: prompt builder (context → prompt string snapshots), JSON validator, suppression.

DoD: forced run produces a real personalised nudge on the phone; forced 00:05 run produces
tonight's report; dry-run archive on a fixture month verifies counts.

## P5 — Actions fallbacks + backup (1.5 h)

- [ ] `fallback-nudge.yml` (cron `50 1-16 * * *` UTC) — queries API; template push on silence.
- [ ] `fallback-report.yml` (cron `15 19 * * *` UTC) — stats report + 1st-of-month archive check.
- [ ] `backup.yml` (Sun 20:30 UTC) — pg_dump (forge_backup) → encrypted artifact 90 d.
- [ ] `ci.yml` gitleaks + ruff + pytest; `deploy-pages.yml`.

DoD: each workflow run manually once, verified on phone / artifacts; a simulated "Rig 2 off"
hour produces exactly one fallback nudge (no double-send when Rig 2 is on).

## P6 — Hardening pass (1.5 h)

Execute Security.md §10 checklist top to bottom, including: second seed user cross-read test
(RLS), CORS/headers curl audit, 429 verification, rotation runbooks (token + VAPID) executed,
backup restored to local Postgres once.

DoD: checklist all green, committed as checked in Security.md.

## P7 — Ship + burn-in (1 h active + 48 h passive)

- [ ] Real data starts: log day 1, watch 07:00 morning nudge kick off yesterday's plan.
- [ ] 48 h burn-in per PRD §8; simulate month-close on staging data once.
- [ ] Record burn-in results in Tracker.md; v1 tagged.

## Session handoff

Every session: read PRD → TechSpec → Schema before any code; work exactly one phase; its DoD
is the acceptance gate. Three invariants must never regress: the purge invariant, pull-only
Rig 2, sanitized LLM output. End every session with Tracker.md updated and a deployable
commit (Rules R7).

## Cut list (if over budget, cut in this order)

yearly PDF compile → privacy toggle → F9 dashboard strip → expense amount field (keep raw text)
→ fallback-nudge template variety. Never cut: purge invariant tests, auth, sanitization, S1.
