# TechSpec — Forge v1

Stack mirrors Blueprint v2.1 Tracks 5–6 so building Forge doubles as practice reps.

## 1. Stack

| Layer | Choice | Why / notes |
|---|---|---|
| Frontend | Vanilla JS PWA (no framework, no build step) | `/web`: index.html, app.js, sw.js, manifest.webmanifest, vendored libs |
| PDF | jsPDF (vendored) | client-side monthly/yearly export |
| Markdown render | marked + DOMPurify (vendored) | reports/nudges are LLM output → always sanitized (Security §6) |
| Hosting (web) | GitHub Pages via Actions | free, HTTPS, anywhere |
| API | FastAPI · Python 3.12 · Pydantic v2 · SQLAlchemy 2 async + asyncpg · slowapi · structlog | Blueprint Track 5 stack |
| API hosting | Render free web service, Docker (multi-stage) | sleeps after idle; cold start 60–120 s tolerated |
| DB | Supabase Postgres (free) | RLS day 1; connect via Supabase **session pooler**; asyncpg `statement_cache_size=0` |
| LLM | Ollama `qwen2.5:7b-instruct` (Q4_K_M) on Rig 2 | fallback model if RAM-tight: `llama3.2:3b` |
| Agent | Python package `/agent` on Rig 2, Windows Task Scheduler | pull-only; pywebpush sender |
| Fallbacks/CI | GitHub Actions | cron jobs, ruff+pytest+gitleaks, weekly backup |
| Push | Web Push, VAPID (`py_vapid` keygen), subject `mailto:sahilch7359@gmail.com` | public key in client; private key only Rig 2 `.env` + Actions secrets |

**Timezone rule:** DB stores UTC (`timestamptz`). All business logic (day boundaries, windows,
"today") computes in `Asia/Kolkata`. A "day" is [00:00, 24:00) IST.

## 2. Repo layout (monorepo `forge`)

```
forge/
├── web/                  # PWA (deployed to Pages)
│   ├── index.html  app.js  sw.js  manifest.webmanifest
│   ├── vendor/           # marked.min.js dompurify.min.js jspdf.umd.min.js (no CDN at runtime)
│   └── icons/            # 180/192/512 + maskable
├── api/
│   ├── app/              # main.py routes/ models.py schemas.py auth.py ratelimit.py db.py config.py
│   ├── migrations/       # 001_init.sql ... (plain SQL, applied by scripts/migrate.py)
│   ├── tests/            # pytest
│   └── Dockerfile  requirements.txt  render.yaml
├── agent/
│   ├── forge_agent/      # context.py llm.py nudge.py report.py archive.py push.py config.py
│   ├── prompts/          # nudge_system.txt report_system.txt  (hand-written — Rules.md R1)
│   ├── tests/  requirements.txt  .env.example
│   └── tasks/            # register_tasks.ps1 (Task Scheduler setup)
├── .github/workflows/    # ci.yml deploy-pages.yml fallback-nudge.yml fallback-report.yml backup.yml
└── docs/                 # this package
```

## 3. API spec (prefix `/v1`, JSON, bearer auth)

Two static tokens v1 (≥ 32 random bytes, constant-time compare): `USER_TOKEN` (phone),
`AGENT_TOKEN` (Rig 2 + Actions fallbacks). Scopes enforced per route.

| Method & path | Auth | Purpose |
|---|---|---|
| POST `/logs` | user | create log `{type, text, data{}}` → server sets ts, user_id |
| GET `/logs?from&to` | user | list (IST-day params) |
| GET `/today` | user | today's logs + stats + streak + day counter + pending tasks |
| POST `/tasks` · PATCH `/tasks/{id}` | user | create / close (`status`, `closed_ts`) |
| GET `/tasks?status=pending` | user | pending list |
| GET `/reports?from&to` · GET `/reports/{date}` | user | daily reports |
| GET `/archives` · GET `/archives/{ym}` | user | monthly archives (md + raw + stats) |
| POST `/push/subscriptions` · DELETE `.../{id}` | user | store/remove Web Push subscription |
| GET `/push/subscriptions` | agent | list live subscriptions (nudge/report/fallback senders) |
| GET `/context` | agent | full LLM context bundle (see §5) |
| POST `/nudges` | agent | record sent nudge |
| POST `/reports` | agent | store daily report (kind daily/daily_fallback) |
| POST `/archives/monthly` | agent | store archive `{ym, md, raw, stats, counts}` |
| POST `/purge` | agent | body `{ym}`; executes verify-then-delete per Schema §5 |
| GET `/healthz` | none | liveness (also used to warm cold starts) |

Errors: RFC-ish `{error: {code, message}}`; 401 unauth, 403 wrong scope, 422 validation,
429 rate-limited. Limits: body ≤ 32 KB; `logs.text` ≤ 4000 chars; rate 60 req/min/token,
10 req/min per-IP for 401s; per-user quota 500 logs/day (sharing-ready).

## 4. Scheduling (all sources of truth)

| Job | Where | Schedule | Action |
|---|---|---|---|
| Hourly nudge | Rig 2 Task Scheduler | :00, 07:00–22:00 IST | context → suppression check → Ollama → push → POST /nudges |
| Daily report | Rig 2 | 00:05 IST | day context → Ollama → POST /reports → push `report_ready` |
| Monthly archive | Rig 2 | 1st, 00:25 IST | build+POST archive → POST /purge |
| Fallback nudge | Actions `fallback-nudge.yml` | cron `50 1-16 * * *` UTC (= 07:20–22:20 IST) | if no nudge AND no log in last 70 min → template push |
| Fallback report | Actions `fallback-report.yml` | cron `15 19 * * *` UTC (= 00:45 IST) | if yesterday(IST) has no report → stats-only report + push; on the 1st also verify archive exists, else alert push |
| Backup | Actions `backup.yml` | Sun 20:30 UTC | pg_dump via read-only role → encrypted artifact, 90-day retention |
| CI | Actions `ci.yml` | on push/PR | ruff, pytest, gitleaks |
| Pages deploy | Actions `deploy-pages.yml` | on push to main (`web/**`) | publish PWA |

Fallback jobs call the API with `AGENT_TOKEN` (single trust path; retry through cold start).
Backup is the only direct-DB consumer: dedicated read-only role.

## 5. Nudge engine

**Context bundle** (`GET /context`):
```json
{
  "now_ist": "...", "day_counter": 12, "day_total": 84, "streak": 9,
  "window": {"start": 7, "end": 22},
  "last_log_min_ago": 132, "escalation": 2,
  "deep_work": {"active": false, "until": null},
  "todays_logs": [{"ts": "...", "type": "checkin", "text": "..."}],
  "pending_tasks": [{"title": "...", "age_hours": 26}],
  "yesterday_plan": ["..."], "last_nudges": ["...", "...", "..."],
  "expenses_today": 480
}
```
**Suppression (deterministic, tested; evaluated before any LLM call):**
1. outside active window → skip  2. `last_log_min_ago` < 25 → skip
3. last nudge < 50 min ago → skip  4. deep-work block active (declared via chip
`data.block_minutes`; silent until block end + 15 min) → skip.

**Escalation ladder** (server-computed, passed to prompt): L0 < 60 min silent · L1 1–2 h ·
L2 2–4 h (direct question about the named pending item) · L3 ≥ 4 h → **hard mode** (blunt,
names the avoidance pattern, quotes Ch. 12 language; still ends with the smallest next action;
never triggered by a *logged* bad day). Morning first nudge = yesterday's plan kickoff.

**LLM call:** qwen2.5:7b-instruct, temp 0.6, max ~120 tokens, JSON output
`{"title": "≤40 chars", "body": "≤220 chars"}` (schema-validated; one retry on invalid JSON,
then template fallback). Anti-repetition: last 3 nudges included with "do not reuse phrasing".
Report call: temp 0.4, max ~900 tokens, markdown with fixed section headers (PRD F3).
Prompts live in `/agent/prompts/` — hand-written (Rules.md R1); user log text is fenced as
untrusted data inside the prompt (Security §6).

## 6. Error handling & resilience

- Agent HTTP: tenacity retry — 5 attempts, exp backoff 2→60 s (absorbs Render cold start ≤ 150 s).
- Ollama down / timeout 90 s → nudge skipped (Actions fallback covers), report → next-morning
  retry at 07:00 before the morning nudge; fallback report already fired at 00:45.
- Push failures: 404/410 → mark subscription dead after 3 consecutive failures; log the rest.
- Offline PWA: IndexedDB queue, replay on `online`; idempotency via client-generated log UUID.
- Supabase pause (7-day idle) prevented by daily traffic; backup restores if it ever archives.

## 7. Observability & testing

- structlog JSON on API + agent; nudges/reports tables double as an audit trail (what/when/model/latency).
- pytest minimum bar (CI-gated): auth + scope middleware; suppression matrix; escalation compute;
  archive completeness (counts/min/max ts); **purge invariant** (never deletes unarchived rows);
  JSON-schema validation of LLM output handling.
- Optional v1.1: Langfuse tracing on agent LLM calls (Track 6 practice, parked).

## 8. Free-tier budget check

~50 user requests/day + 16 nudges + 3 crons ≈ trivial vs Render 750 h/mo (one always-on service),
Supabase 500 MB (raw month ≈ a few MB; archives grow ~1–3 MB/yr), Actions ~450 min/mo used of
2000 free, Pages 1