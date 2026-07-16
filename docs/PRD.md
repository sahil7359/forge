# PRD — Forge v1

**Owner:** Sahil Chakraborty · **Status:** locked for build · **Date:** 2026-07-15
**One-liner:** an hourly AI accountability coach on the iPhone lock screen, powered entirely by free tiers and a local LLM, tracking a 12-week build sprint.

## 1. Problem

A 12-week build sprint demands 6–8 h/day of focused build time and a strict daily check-in ritual.
Manual rituals decay: motivation dips mid-afternoon, pending tasks slip silently, and there is no
accountability at hour granularity. Generic reminder apps nag without context; they don't know what
was shipped at 13:10 or that yesterday's task is still open. Cloud AI coaches cost money and see
private data. Sahil owns idle GPU hardware (Rig 2) that can do this locally for free.

## 2. User

v1: exactly one user (Sahil). iPhone (iOS ≥ 16.4), Windows PCs, IST timezone.
v2 (explicitly designed-for, not built): small invited group — see §7 and Security.md §9.

## 3. Goals & success metrics

| Goal | Metric | Target |
|---|---|---|
| Log consistently | check-ins per active day | ≥ 5 |
| Nudges convert to action | nudge → log within 45 min | ≥ 40% |
| Reports get read | daily report opened | ≥ 6 of 7 days |
| Zero data loss | purge-invariant violations | 0, ever |
| Stays a tool | total build time to v1 | ≤ 16 h |
| Reliability | days with zero nudges delivered (07–22 IST) | 0 (fallback covers Rig 2 downtime) |

## 4. Features (MoSCoW)

### Must (v1)
- **F1 — Quick log, unstructured-first.** One text box; whatever the user types is a check-in.
  Optional chips add light structure: `task` (creates a pending task), `expense` (amount field),
  `fitness`, `habit`, `deep-work block` (minutes). Text ≤ 4000 chars.
- **F2 — Hourly LLM nudge (07:00–22:00 IST).** Ollama on Rig 2 reads today's logs, pending tasks,
  yesterday's plan, streak, last 3 nudges → generates title+body push. Tone: adaptive coach,
  escalating with silence; **hard mode** at ≥ 4 h silent (blunt, names avoidance patterns;
  never shaming a *logged* bad day — a stuck day still pushes).
  Suppression: skip if last log < 25 min ago, min 50 min between nudges, silent during declared
  deep-work blocks (+15 min grace). Morning nudge kicks off yesterday's plan.
- **F3 — Midnight report (00:05 IST).** LLM report: shipped today, blockers, numbers (minutes,
  expenses, workouts), streak & gate countdown, tomorrow's plan (≤ 3 items), one hard truth.
  Push "report ready"; readable in-app.
- **F4 — Month-boundary retention.** Raw logs/nudges/daily reports live in DB for the current
  month + previous month until archived. On the 1st, 00:25 IST: full-fidelity monthly archive
  (rendered markdown + verbatim raw JSON incl. **all timestamps** + stats), then purge archived
  raw rows. Purge runs **only after archive verified** (see Schema.md §5 invariant).
- **F5 — Downloadable reports.** Monthly archive → PDF, generated client-side. Yearly = compiled
  on demand from monthly archives, with full timestamp appendix.
- **F6 — Push pipeline.** Web Push (VAPID) to installed PWA; iOS ≥ 16.4.
- **F7 — Fallback layer.** GitHub Actions: template reminder at :20 if no nudge/log in 70 min;
  stats-only report at 00:45 if Rig 2 missed midnight; archive check on the 1st.
- **F8 — Offline logging.** Queue in IndexedDB, sync on reconnect (Render cold starts tolerated).

### Should (v1 if budget allows)
- **F9 — Today dashboard strip.** Day N/84, streak, pending task count, expenses today.
- **F10 — Settings.** Active window, nudge gap, hard-mode threshold, test-push button, token entry.

### Won't (v1) — parked in Tracker.md → Someday
- Multi-user signup (designed-for only), Supabase Auth, chat-with-coach, Langfuse tracing,
  Cloudflare tunnel, habit analytics/charts, Android, App Store wrapper, RAG over logs.

## 5. Retention requirement (verbatim intent)

Only ~1 month of raw check-ins stays in the DB. Monthly reports persist forever and contain
**every detail including every timestamp** — they are the archive of record. Yearly view compiles
all monthlies. Deletion is subordinate to archival: no verified archive → no purge, fallback alerts.

## 6. Constraints

- ₹0 infrastructure: GitHub Pages + Actions, Render free (sleeps → cold starts accepted), Supabase
  free (daily traffic prevents pause), Ollama on owned hardware.
- iOS PWA rules: push only after Add to Home Screen, iOS ≥ 16.4; no reliable local scheduling —
  all notifications are server-sent.
- Rig 2 availability: nudges/reports degrade to fallback quality when it's off. Acceptable.
- GitHub cron drift (±5–15 min) acceptable for fallbacks.
- Build effort ≤ 16 h (a tool must never displace the primary work it exists to support).

## 7. Sharing-readiness principle (v2 direction)

Every table carries `user_id` from migration 001; RLS enforced per-user from day 1; auth is a
swappable dependency (static bearer v1 → Supabase Auth JWT v2); per-user quotas and invite codes
specified in Security.md §9. Rig 2 LLM capacity model: ~30–60 s per nudge → cap ~8–10 beta users
before model downsizing or queueing. No production promise beyond that without new hosting.

## 8. Acceptance (v1 ships when)

All POC.md spikes pass → ImplementationPlan P0–P7 done → 48 h burn-in: every waking hour produced
a nudge (LLM or fallback), midnight produced a report, one simulated month-close produced a
verified archive + purge on staging data, and Security.md checklist §10 is green.
