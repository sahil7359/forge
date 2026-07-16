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
| P5 Actions fallbacks + backup | 1.5 h | not started | — |
| P6 Hardening (Security §10) | 1.5 h | not started | — |
| P7 Ship + 48 h burn-in | 1 h | not started | — |
| **Total** | **16 h** | | |

## POC results (fill during P1)

| Spike | Gate | Result | Numbers |
|---|---|---|---|
| S1 iOS push | lock-screen delivery, app closed, cellular + post-reboot | — | — |
| S2 Ollama | p95 < 60 s, valid JSON ≥ 8/10, no hallucinated events | **green on Rig 1** — re-verify on Rig 2 (2060 Super) before P4 sign-off | model: qwen2.5:7b-instruct · tok/s: 141 · p95: 0.61 s · 10/10 valid JSON · 10/10 anchored · model load 32.6 s · 6.6 GB VRAM (measured on Rig 1 5070 Ti — ~100x gate margin, low risk on 2060S) |
| S3 Cold start | agent survives ≤ 150 s, 3/3 | 3 timed cycles running (results → phase-reports/spikes/s3_results.txt) | wake times: |

## Session log

| Date | Phase | Shipped | Blockers | Min |
|---|---|---|---|---|
| 2026-07-15 | docs | Full docs package v1 (PRD, TechSpec, AppFlow, Design, Schema, Security, POC, Plan, Rules, Tracker) | — | — |
| 2026-07-15 | P0 | branch→`main`; venv + deps; USER/AGENT tokens + VAPID keypair → gitignored `.env`s + `secrets/`; qwen2.5:7b-instruct pulled; ruff+pytest+gitleaks green local; `/healthz` 200 local; fixes: migrate.py ASYNC240, tzdata dep (Windows zoneinfo) | cloud accounts (see Blockers); first token set echoed into terminal output by a pytest traceback → all secrets regenerated, leaked set never deployed | 35 |

| 2026-07-16 | P0 done · P1 | public-showcase scrub (personal refs removed; contact → help.sahil.gob@gmail.com); P0 DoD verified (healthz · Pages 200 · qwen2.5); S1 spike page live (VAPID key wired, subscription JSON shown pre-API); S2 **green**: p95 0.61 s, 10/10 valid JSON, 141 tok/s | S1 awaits iPhone; S3 awaits real Render URL | 45 |
| 2026-07-16 | P1–P3 | second personal-info pass (Blueprint/plan refs out; contact email swapped everywhere incl. seed + VAPID); S2 numbers re-attributed to Rig 1 (5070 Ti) — re-verify on Rig 2; S3 3-cycle measurement running against forge-tuvr.onrender.com; **P2 shipped**: auth/RLS/routes/limits/purge-proposal + migration 004, 75 tests, deployed, no-auth walkthrough green (CORS exact-origin verified), authed walkthrough blocked on 004; **P3 shipped**: full PWA deployed to Pages (composer+chips, offline IndexedDB queue w/ self-heal fix found in browser testing, sanitized reports w/ XSS verified inert, monthly+yearly jsPDF, sw shell cache, /settings API) | migration 004 (owner, SQL editor); S1 iPhone steps; Rig-2 S2 re-run; walkthrough re-run post-004 | 150 |

| 2026-07-16 | P4 | agent package complete: nudge/report/archive jobs (AppFlow 3/5/6), Ollama contract (down→skip, invalid→retry→template), prompt builder with fenced untrusted logs (injection-neutralized, snapshot-tested), client-side suppression mirror, deterministic LLM-free archive builder (server counts verbatim); API adds agent-scope /v1/export + subscription-failure route; report job idempotent for the 07:00 retry task (added to register_tasks.ps1); real-qwen pipeline verified at 3 escalation levels (0.5–2.5 s) | P4 DoD needs: 004 → S1 → Rig 2 clone + register_tasks → forced runs | 60 |

**Next single task:** owner clears Blockers 1–2 (migration 004 + S1 iPhone test) → deploy agent to Rig 2 (clone, venv, `agent/.env`, `register_tasks.ps1`, re-run S2 there) → forced nudge + forced report on the phone = P4 DoD → P5.

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

## Blockers

1. **Migration 004** (owner, 1 min): Supabase SQL editor → run `api/migrations/004_users_lookup.sql`
   (needs postgres role; forge_api can't create policies). Every authed route 500s until then.
   Then re-run `phase-reports/spikes/p2_walkthrough.py` → expect 21/21.
2. **S1 iPhone steps** (owner): install PWA from `https://sahil7359.github.io/forge/`, paste
   USER_TOKEN in Settings, Enable notifications, then `s1_send_push.py` from this machine.
3. **S2 re-verify on Rig 2** (2060 Super) before P4 sign-off — current numbers are from Rig 1.
4. Consistency (non-blocking): Actions secret `VAPID_SUB` → mailto:help.sahil.gob@gmail.com;
   Supabase: `update users set email='help.sahil.gob@gmail.com' where email like 'sahil%';`

## Someday (parked — Rules R2, do not start before v1 ships)

- Supabase Auth + invite codes (sharing mode, Security §9)
- Chat-with-coach (PWA ↔ Ollama, needs tunnel design — conflicts with pull-only rule, think hard)
- Langfuse tracing on agent (Track 6 practice)
- Habit/expense charts; weekly Sunday review auto-draft
- Apple Shortcuts quick-log (POST /logs from share sheet)
- Android/desktop layouts; App Store wrapper via Capacitor
- RAG over archives ("what did I ship in week 3?")
