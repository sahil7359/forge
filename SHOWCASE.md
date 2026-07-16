# Forge — engineering showcase

A single-user (multi-user-ready) accountability coach: an iPhone PWA that receives hourly,
context-aware nudges written by a **local LLM**, plus a nightly report and a permanent
monthly archive — running end to end on **free infrastructure** with all intelligence on a
home GPU that is never exposed to the internet.

> Live API: `https://forge-tuvr.onrender.com/healthz` · PWA: `https://sahil7359.github.io/forge/`
> 133 automated tests (80 API + 53 agent) · CI: ruff + pytest + gitleaks on every push.

This document is the guided tour. It exists to be read in ten minutes and to make the
design decisions legible.

---

## 1. The problem and the shape of the solution

Daily build discipline decays without accountability at the right granularity. Generic
reminder apps nag without context; cloud AI coaches cost money and read private data. Forge
answers with an hourly coach that **knows what you actually did** (it reads your day's logs),
**escalates as you go silent**, and **runs the model on hardware you own** so your data never
leaves your control.

Three hard constraints drove every decision:
1. **₹0 infrastructure** — free tiers only (Render, Supabase, GitHub Pages/Actions, Ollama on owned GPU).
2. **The home machine is never reachable from the internet** — it only makes outbound calls.
3. **The LLM is untrusted** — its output is sanitized everywhere and can never take an action.

---

## 2. Architecture

```
   iPhone PWA  ──HTTPS + bearer──►  FastAPI on Render  ──asyncpg + RLS──►  Supabase Postgres
  (GitHub Pages)                    (free web service)                    (free, RLS on day 1)
        ▲                                  ▲     ▲
        │ Web Push (VAPID)                 │     │ outbound only
        │                                  │     │
   home Windows "Rig 2"  ──pull────────────┘     └──── GitHub Actions (fallback layer + CI + backup)
   Python agent + Ollama (qwen2.5:7b)             hourly template nudge if Rig 2 is offline;
   hourly nudge · nightly report · monthly        nightly stats report; weekly encrypted pg_dump
   archive+purge — Windows Task Scheduler
```

**Trust model in one line:** everything writes through the API boundary; only the weekly
backup reads the database directly (dedicated read-only role); the home GPU initiates every
connection, so no inbound path to the home network exists.

**Why three compute tiers instead of one:** the LLM must be local (privacy + cost), the API
must be always-reachable (the phone talks to it), and there must be a dumb fallback for when
the home machine sleeps. Each tier does the one thing it's best placed to do.

---

## 3. Full technology stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vanilla JS PWA, **no build step, no framework** | installable on iOS, offline-capable, zero toolchain, CSP-friendly (vendored libs only) |
| PWA libs (vendored, no CDN) | marked 15, DOMPurify 3.4, jsPDF 2.5 | markdown render + sanitize + client-side PDF; committed so CSP can be `default-src 'self'` |
| API | **FastAPI · Python 3.12 · Pydantic v2 · async end-to-end** | typed boundaries, async I/O, small surface |
| DB access | SQLAlchemy 2 Core (async) + asyncpg | plain SQL, no ORM magic; `statement_cache_size=0` for Supabase's pooler |
| Database | Supabase Postgres, **Row-Level Security from migration 001** | per-user isolation enforced in the database, not just app code |
| LLM | **Ollama `qwen2.5:7b-instruct`** on RTX 2060 Super | local, free, private; JSON-mode nudges + markdown reports |
| Agent | Python package on Windows Task Scheduler | pull-only; tenacity retries absorb API cold starts |
| Push | Web Push + VAPID (`py_vapid`, `pywebpush`) | works on installed iOS PWAs; private key only on the home box + Actions |
| Hosting | Render (API, Docker) · GitHub Pages (PWA) · Supabase (DB) | all free tiers |
| Automation | GitHub Actions | fallback jobs (cron), CI, weekly encrypted backup, Pages deploy |
| Tooling | ruff (lint+format) · pytest · gitleaks · pip-audit | one style authority, table-driven tests, secret + CVE scanning |
| Observability | structlog (JSON) + the nudges/reports tables as an audit trail | every nudge records model, latency, escalation |

---

## 4. Code structure

```
forge/
├── api/                         FastAPI service (deployed to Render)
│   ├── app/
│   │   ├── main.py              app wiring: middleware order, error shape, structlog
│   │   ├── auth.py              two static bearer tokens, constant-time, scope-separated
│   │   ├── db.py                async engine; per-request tx sets app.user_id for RLS
│   │   ├── ratelimit.py         sliding-window limiter (per token / per forwarded-IP)
│   │   ├── schemas.py           Pydantic v2 request models — every input length-capped
│   │   ├── config.py            env-driven settings (pydantic-settings)
│   │   ├── core/
│   │   │   ├── time.py          ALL IST day-boundary math (the only place "today" is computed)
│   │   │   ├── nudge_rules.py   escalation ladder · suppression · deep-work · streak (pure fns)
│   │   │   └── purge.py         verify-before-purge executor — the sacred invariant
│   │   └── routes/              logs · tasks · reports · push · settings · export · agent(/context,/nudges,/purge)
│   ├── migrations/              001 schema · 002 RLS · 003 seed · 004 lookup policy · manual/000 roles
│   ├── tests/                   auth matrix · suppression/escalation tables · purge invariant · limits
│   ├── Dockerfile · render.yaml · requirements.txt
│
├── agent/                       Rig 2 package (home GPU) + Actions fallback entrypoints
│   ├── forge_agent/
│   │   ├── llm.py               Ollama client + JSON contract (retry → deterministic template)
│   │   ├── context.py           prompt builder — fences untrusted log text, snapshot-tested
│   │   ├── rules.py             client-side suppression re-check (defense in depth)
│   │   ├── nudge.py report.py archive.py   the three scheduled jobs
│   │   ├── fallback.py          LLM-free Actions jobs (nudge / report / archive watchdog)
│   │   ├── http.py              tenacity API client (absorbs Render cold start)
│   │   ├── push.py              VAPID Web Push sender
│   │   └── istime.py            agent-side IST helpers
│   ├── prompts/                 nudge_system.txt · report_system.txt (hand-written voice)
│   ├── tasks/register_tasks.ps1 Task Scheduler setup (wake-to-run, run-if-missed)
│   └── tests/                   prompt snapshots · JSON validator · suppression · archive counts
│
├── web/                         PWA (deployed to GitHub Pages)
│   ├── index.html app.js sw.js manifest.webmanifest   Today/Reports/Settings, offline queue, PDF
│   └── vendor/                  marked · DOMPurify · jsPDF (committed, no runtime CDN)
│
├── .github/workflows/          ci · deploy-pages · fallback-nudge · fallback-report · backup
└── docs/                        PRD · TechSpec · Schema · Security · Threats · AppFlow · Design · Runbooks · Tracker
```

---

## 5. Engineering decisions worth talking about

These are the parts that separate "a working app" from "an engineered system."

**Verify-before-purge (a data-loss-proof deletion invariant).** Raw logs live ~1 month; on
the 1st, the agent builds a full-fidelity monthly archive (every row, every timestamp) and
only *then* asks the API to delete. The API independently re-counts live rows, refuses to
delete unless counts match the archive exactly, deletes inside one transaction, and rolls
back if the deleted count disagrees. No verified archive → no deletion, ever. It's isolated
in `core/purge.py` behind a repo protocol so the invariant is unit-tested without a database
(archive-missing, count-mismatch, delete-mismatch, happy-path).

**Row-Level Security from day one.** Every table carries `user_id`; every request runs inside
a transaction whose first statement sets `app.user_id`, and Postgres RLS policies scope all
queries. Authorization is enforced in the database, so the app is multi-user-ready without a
rewrite — auth is a one-file swap point (static token today → Supabase JWT later).

**The LLM is treated as hostile.** User log text is fenced as data inside prompts (with the
closing tag escaped so it can't break out), the system prompt says the fence is untrusted,
and the model has **zero tools** — it only emits text, so even a successful prompt injection
can't take an action. Output is JSON-schema-validated with one retry then a deterministic
fallback; rendered only through DOMPurify under a `default-src 'self'` CSP; push payloads are
plain-text and length-capped. (XSS probes verified inert in-browser.)

**Graceful degradation is designed, not hoped for.** The home GPU sleeps? A GitHub Actions
cron sends a template nudge — but only when the real agent has been silent 70+ minutes, so it
never double-sends. Ollama down? The hour is skipped and the fallback covers it. Render cold?
The agent's tenacity backoff absorbs it (measured: 12–13 s wakes vs a 150 s budget). Phone
offline? Logs queue in IndexedDB with client-generated UUIDs and replay idempotently on
reconnect.

**Time is computed in exactly one place.** All "what day is it" logic lives in `core/time.py`
(Asia/Kolkata); the database stores UTC; the client never decides the date. Day boundaries,
month spans, and streaks all derive from that single module — table-tested including the
December→January and leap-February edges.

**Test what regresses silently.** Table-driven tests cover the suppression matrix, escalation
ladder, and purge invariant; prompt-builder **snapshot** tests catch silent context drift; the
LLM contract is tested through valid/invalid/timeout paths without ever depending on model
quality in CI.

---

## 6. Security posture

Documented threat model in `docs/Threats.md`, checklist in `docs/Security.md §10`. Highlights:

- **No inbound path to the home network** — the agent is pull-only; the one real exposure found
  in audit (Ollama binding to `0.0.0.0`) is closed by binding to localhost + a firewall block.
- **Secrets** never in the repo (gitleaks CI + full-history scans), only in Authorization
  headers / gitignored `.env` / Render env / Actions secrets; 2FA on all accounts.
- **RLS** enforces per-user isolation in the database; **CORS** locked to the exact Pages
  origin; **security headers** (nosniff, frame-deny, no-referrer) on every response; **rate
  limits** + per-user quotas return 429; **dependencies** CVE-clean (pip-audit).
- Rotation runbooks (token, VAPID) and an encrypted weekly backup with a tested restore path.

---

## 7. Running it

- **API** (local): `cd api && uvicorn app.main:app` → `GET /healthz` → `{"status":"ok"}`.
- **PWA** (local): serve `web/` on any static server; installable via Safari → Add to Home Screen.
- **Tests**: `cd api && pytest` (80) · `cd agent && pytest` (53).
- **Agent** (home GPU): `python -m forge_agent.nudge` produces a real nudge; `--dry-run` on the
  archive job prints counts without writing.
- Full deploy + operations: `docs/Runbooks.md`.

---

## 8. Roadmap

**v1 ship (in progress):** apply the RLS role fix + lookup migration, set Actions secrets,
verify iOS push, deploy the agent to the home GPU, 48-hour burn-in, tag `v1`.

**Designed but deferred (v2+):** multi-user sharing (Supabase Auth JWT — the RLS is already in
place), an LLM-observability/eval loop on the nudge quality, habit/expense analytics, and a
LangGraph reimplementation of the nudge decision flow as a stateful graph. Each is a contained
addition because the boundaries were drawn for it up front.
