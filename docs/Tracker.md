# Tracker — Forge (living document)

Update at the end of every session (Rules R7).

## Phase status

| Phase | Budget | Status | Actual |
|---|---|---|---|
| P0 Accounts, keys, scaffold | 1 h | done (healthz live · Pages live · qwen2.5 pulled) | ~1 h |
| P1 POC spikes (S1 push · S2 Ollama · S3 cold start) | 2.5 h | S2 green · S1 awaits iPhone · S3 cycles running | 0.5 h |
| P2 DB + API core | 3 h | deployed; 75 tests green; walkthrough blocked on migration 004 | 1.5 h |
| P3 PWA | 3 h | built + deployed to Pages; browser-verified; iPhone DoD pending | 1.5 h |
| P4 Agent on Rig 2 | 2.5 h | built + tested (42 agent tests); Rig 2 deploy + forced-run DoD pending | 1 h |
| P5 Actions fallbacks + backup | 1.5 h | code + workflows + tests done; manual runs blocked on Actions secrets | 0.5 h |
| P6 Hardening (Security §10) | 1.5 h | machine checks done; 2 findings (proxy-IP keying fixed · postgres-role DB URL caught); owner items open | 0.5 h |
| P7 Ship + burn-in | 1 h | burn-in checklist ready (phase-reports) | — |
| **Total** | **16 h** | | |

## POC results (fill during P1)

| Spike | Gate | Result | Numbers |
|---|---|---|---|
| S1 iOS push | lock-screen delivery, app closed, cellular + post-reboot | — | — |
| S2 Ollama | p95 < 60 s, valid JSON ≥ 8/10, no hallucinated events | **green on Rig 1** — re-verify on Rig 2 (2060 Super) before P4 sign-off | model: qwen2.5:7b-instruct · tok/s: 141 · p95: 0.61 s · 10/10 valid JSON · 10/10 anchored · model load 32.6 s · 6.6 GB VRAM (measured on Rig 1 5070 Ti — ~100x gate margin, low risk on 2060S) |
| S3 Cold start | agent survives ≤ 150 s, 3/3 | **green** (2026-07-16) — Actions-job sub-check lands with P5 | wake times: 13 s · 13 s · 12 s (40 min–4.8 h idle; first attempt each, zero retries; tenacity budget 150 s barely touched) |

## Session log

| Date | Phase | Shipped | Blockers | Min |
|---|---|---|---|---|
| 2026-07-15 | docs | Full docs package v1 (PRD, TechSpec, AppFlow, Design, Schema, Security, POC, Plan, Rules, Tracker) | — | — |
| 2026-07-15 | P0 | branch→`main`; venv + deps; USER/AGENT tokens + VAPID keypair → gitignored `.env`s + `secrets/`; qwen2.5:7b-instruct pulled; ruff+pytest+gitleaks green local; `/healthz` 200 local; fixes: migrate.py ASYNC240, tzdata dep (Windows zoneinfo) | cloud accounts (see Blockers); first token set echoed into terminal output by a pytest traceback → all secrets regenerated, leaked set never deployed | 35 |

| 2026-07-16 | P0 done · P1 | public-showcase scrub (personal refs removed; contact → help.sahil.gob@gmail.com); P0 DoD verified (healthz · Pages 200 · qwen2.5); S1 spike page live (VAPID key wired, subscription JSON shown pre-API); S2 **green**: p95 0.61 s, 10/10 valid JSON, 141 tok/s | S1 awaits iPhone; S3 awaits real Render URL | 45 |
| 2026-07-16 | P1–P3 | second personal-info pass (Blueprint/plan refs out; contact email swapped everywhere incl. seed + VAPID); S2 numbers re-attributed to Rig 1 (5070 Ti) — re-verify on Rig 2; S3 3-cycle measurement running against forge-tuvr.onrender.com; **P2 shipped**: auth/RLS/routes/limits/purge-proposal + migration 004, 75 tests, deployed, no-auth walkthrough green (CORS exact-origin verified), authed walkthrough blocked on 004; **P3 shipped**: full PWA deployed to Pages (composer+chips, offline IndexedDB queue w/ self-heal fix found in browser testing, sanitized reports w/ XSS verified inert, monthly+yearly jsPDF, sw shell cache, /settings API) | migration 004 (owner, SQL editor); S1 iPhone steps; Rig-2 S2 re-run; walkthrough re-run post-004 | 150 |

| 2026-07-16 | P4 | agent package complete: nudge/report/archive jobs (AppFlow 3/5/6), Ollama contract (down→skip, invalid→retry→template), prompt builder with fenced untrusted logs (injection-neutralized, snapshot-tested), client-side suppression mirror, deterministic LLM-free archive builder (server counts verbatim); API adds agent-scope /v1/export + subscription-failure route; report job idempotent for the 07:00 retry task (added to register_tasks.ps1); real-qwen pipeline verified at 3 escalation levels (0.5–2.5 s) | P4 DoD needs: 004 → S1 → Rig 2 clone + register_tasks → forced runs | 60 |

| 2026-07-16 | P5+P6 | fallback.py complete (Rig-2-off decision matrix, stats-only report, month-close watchdog; 11 new tests — 53 agent total); workflows already scaffold-complete; Runbooks.md (rotations, restore, DB-role check, task re-register); Security §10: 5/9 verified+checked; **P6 findings:** (1) per-IP rate windows dead behind Render's proxy → X-Forwarded-For keying + tests (80 api total), (2) DATABASE_URL connects as postgres/bypassrls → RLS effectively off for the API → Runbooks R-4 fix owner-side; RLS cross-read script ready | owner Blockers list rebuilt (9 items, ordered) | 60 |

**Next single task:** owner runs Blockers 1–4 (DB role fix → 004 → verify scripts → Actions secrets), then Rig 2 deploy per phase-reports/RIG2-SETUP.md → P4/P5 DoDs → P6 close → P7 burn-in.

**Process note:** every phase ends with an in-depth private report in `phase-reports/` (gitignored — never commit), containing blockers, incidents, evidence, owner to-dos, and the next phase's run command. P0 report exists.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-07-15 | PWA over native iOS | no Mac dependency, $0, Web Push works on iOS ≥ 16.4 |
| 2026-07-15 | Name: Forge | forging daily discipline into shipped work |
| 2026-07-15 | Python/FastAPI stack | typed async Python; practice reps while building |
| 2026-07-15 | All intelligence on Rig 2 (hourly + midnight), Actions = dumb fallback | local LLM requirement; simplest trust model; pull-only home network |
| 2026-07-15 | qwen2.5:7b-instruct primary, llama3.2:3b fallback | Rig 2 2060 Super capability (verify in S2) |
| 2026-07-15 | Month-boundary retention + permanent full-fidelity archives | owner requirement: ~1 month raw, monthly reports keep every timestamp |
| 2026-07-15 | Nudge tone: adaptive, hard mode at ≥ 4 h silence | owner choice; blunt language allowed |
| 2026-07-15 | user_id + RLS from migration 001 | future sharing without rearchitecting; Security §9 |
| 2026-07-15 | Fallback jobs call API (not DB) | single trust path; only backup touches DB read-only |

## Blockers (owner actions — ordered; details in phase-reports/RIG2-SETUP.md)

1. **DATABASE_URL role fix** (Runbooks R-4): swap `postgres.<ref>` → `forge_api.<ref>` in
   Render env AND local `api/.env` — P6 found the API connecting as postgres (bypasses RLS).
2. **Migration 004** in the Supabase SQL editor (authed routes 500 until then).
3. Verify: `p2_walkthrough.py` → 21/21 · `p6_rls_crossread.py` → 7/7 (both in phase-reports/spikes/).
4. **Actions secrets** (exact names the workflows read): `API_BASE`, `AGENT_TOKEN`,
   `VAPID_PRIVATE_KEY` (raw b64 — same value as the agent/.env line, NOT the .pem),
   `VAPID_SUBJECT` = mailto:help.sahil.gob@gmail.com, `BACKUP_URL` (forge_backup pooler URL),
   `BACKUP_PASSPHRASE` (new strong passphrase → password manager).
5. **S1 iPhone**: install PWA → token → Enable notifications → `s1_send_push.py`; verify
   lock screen, app closed, cellular, post-reboot.
6. **Rig 2 deploy** per phase-reports/RIG2-SETUP.md (incl. S2 re-run there) → forced
   nudge/report/archive-dry-run = P4 DoD.
7. **P5 DoD**: run each workflow once manually (Actions → Run workflow); then the double-send
   check: with Rig 2 ON, the :20 fallback must log `fallback_skip rig2_alive`.
8. **P6 close**: rotation runbooks R-1/R-2 executed once · backup artifact restored (R-3) ·
   remaining Security §10 boxes checked.
9. Consistency: Supabase `update users set email='help.sahil.gob@gmail.com' where email like 'sahil%';`

## Someday (parked — Rules R2, do not start before v1 ships)

- Supabase Auth + invite codes (sharing mode, Security §9)
- Chat-with-coach (PWA ↔ Ollama, needs tunnel design — conflicts with pull-only rule, think hard)
- Langfuse tracing on agent (Track 6 practice)
- Habit/expense charts; weekly Sunday review auto-draft
- Apple Shortcuts quick-log (POST /logs from share sheet)
- Android/desktop layouts; App Store wrapper via Capacitor
- RAG over archives ("what did I ship in week 3?")
