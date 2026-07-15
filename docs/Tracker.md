# Tracker — Forge (living document)

Update at the end of every session (Rules R7). Format mirrors Blueprint STREAK_LOG.

## Phase status

| Phase | Budget | Status | Actual |
|---|---|---|---|
| P0 Accounts, keys, scaffold | 1 h | in progress — machine-side done, cloud accounts left | 0.6 h |
| P1 POC spikes (S1 push · S2 Ollama · S3 cold start) | 2.5 h | not started | — |
| P2 DB + API core | 3 h | not started | — |
| P3 PWA | 3 h | not started | — |
| P4 Agent on Rig 2 | 2.5 h | not started | — |
| P5 Actions fallbacks + backup | 1.5 h | not started | — |
| P6 Hardening (Security §10) | 1.5 h | not started | — |
| P7 Ship + 48 h burn-in | 1 h | not started | — |
| **Total** | **16 h** | | |

## POC results (fill during P1)

| Spike | Gate | Result | Numbers |
|---|---|---|---|
| S1 iOS push | lock-screen delivery, app closed, cellular + post-reboot | — | — |
| S2 Ollama | p95 < 60 s, valid JSON ≥ 8/10, no hallucinated events | — | model: · tok/s: · p95: |
| S3 Cold start | agent survives ≤ 150 s, 3/3 | — | wake times: |

## Session log

| Date | Phase | Shipped | Blockers | Min |
|---|---|---|---|---|
| 2026-07-15 | docs | Full docs package v1 (PRD, TechSpec, AppFlow, Design, Schema, Security, POC, Plan, Rules, Tracker) | — | — |
| 2026-07-15 | P0 | branch→`main`; venv + deps; USER/AGENT tokens + VAPID keypair → gitignored `.env`s + `secrets/`; qwen2.5:7b-instruct pulled; ruff+pytest+gitleaks green local; `/healthz` 200 local; fixes: migrate.py ASYNC240, tzdata dep (Windows zoneinfo) | cloud accounts (see Blockers); first token set echoed into terminal output by a pytest traceback → all secrets regenerated, leaked set never deployed | 35 |

**Next single task:** owner completes cloud accounts (Blockers list) → verify P0 DoD → start P1 S1 (iOS push spike).

**Process note:** every phase ends with an in-depth private report in `phase-reports/` (gitignored — never commit), containing blockers, incidents, evidence, owner to-dos, and the next phase's run command. P0 report exists.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-07-15 | PWA over native iOS | no Mac dependency, $0, Web Push works on iOS ≥ 16.4 |
| 2026-07-15 | Name: Forge | forging the TCS → GenAI transition |
| 2026-07-15 | Python/FastAPI stack | mirrors Blueprint Tracks 5–6; reps while building |
| 2026-07-15 | All intelligence on Rig 2 (hourly + midnight), Actions = dumb fallback | local LLM requirement; simplest trust model; pull-only home network |
| 2026-07-15 | qwen2.5:7b-instruct primary, llama3.2:3b fallback | Rig 2 2060 Super capability (verify in S2) |
| 2026-07-15 | Month-boundary retention + permanent full-fidelity archives | owner requirement: ~1 month raw, monthly reports keep every timestamp |
| 2026-07-15 | Nudge tone: adaptive, hard mode at ≥ 4 h silence | owner choice; Ch. 12 language allowed |
| 2026-07-15 | user_id + RLS from migration 001 | future sharing without rearchitecting; Security §9 |
| 2026-07-15 | Fallback jobs call API (not DB) | single trust path; only backup touches DB read-only |

## Blockers

P0 owner-account actions (need Sahil's credentials):

1. GitHub: create private repo `forge`; `git remote add origin … && git push -u origin main`;
   enable secret scanning + push protection; 2FA on GitHub, Render, Supabase (Security §5).
2. Supabase: new project (ap-south/Mumbai if offered); SQL editor → run
   `api/migrations/manual/000_roles.sql`, then 001–003 (or `scripts/migrate.py`); copy
   session-pooler DATABASE_URL → `api/.env` + Render env.
3. Render: new web service from repo `api/Dockerfile`; env = DATABASE_URL, USER_TOKEN,
   AGENT_TOKEN, CORS_ORIGIN (values already in local `api/.env`).
4. GitHub Pages: enable (Actions source). Actions secrets: AGENT_TOKEN, VAPID_PRIVATE
   (`secrets/vapid_private.pem`), VAPID_SUB=mailto:sahilch7359@gmail.com, BACKUP_URL, API_BASE.
5. After Render is live: fill `API_BASE` in `agent/.env`.

## Someday (parked — Rules R2, do not start before v1 ships + Project 1 is live)

- Supabase Auth + invite codes (sharing mode, Security §9)
- Chat-with-coach (PWA ↔ Ollama, needs tunnel design — conflicts with pull-only rule, think hard)
- Langfuse tracing on agent (Track 6 practice)
- Habit/expense charts; weekly Sunday review auto-draft (Ch. 12 ritual)
- Apple Shortcuts quick-log (POST /logs from share sheet)
- Android/desktop layouts; App Store wrapper via Capacitor
- RAG over archives ("what did I ship in week 3?")
- Blueprint gate tracking UI (G1–G3 checklists)
