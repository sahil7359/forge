# AppFlow — Forge v1

All times IST. "Phone" = installed PWA on iPhone (iOS ≥ 16.4).

## Flow 1 — Onboarding (once)

1. Open Pages URL in **Safari** → Share → **Add to Home Screen** (push does not work in-browser).
2. Launch from home screen → Settings tab → paste `USER_TOKEN` → Save (stored on device).
3. Tap **Enable notifications** → iOS permission prompt → subscription POSTed to API.
4. Tap **Test push** → notification arrives → onboarding done.
5. Rig 2 side (once): clone repo, `agent/.env` from example, `ollama pull qwen2.5:7b-instruct`,
   run `tasks/register_tasks.ps1` (registers hourly / 00:05 / monthly jobs).

## Flow 2 — Quick log (the core loop, ≤ 10 s)

Open app → big text box → type anything ("finished sliding window 6/8, brain fried") → optional
chip: task / expense (+amount) / fitness / habit / deep-work (+minutes) → Send.
Offline? → saved to IndexedDB queue, banner "will sync", replayed on reconnect (client UUID =
idempotent). Today feed updates instantly (optimistic).

## Flow 3 — Hourly nudge (07:00–22:00, on Rig 2)

1. Task Scheduler fires :00 → agent `GET /context` (retries through Render cold start).
2. Suppression check (deterministic, in order): outside window? logged < 25 min ago? last nudge
   < 50 min ago? deep-work block active (+15 min grace)? → any yes = exit silently.
3. Escalation computed from silence: L0 <1 h · L1 1–2 h · L2 2–4 h (asks about the named pending
   task) · L3 ≥ 4 h hard mode.
4. Ollama generates `{title, body}` (validated; retry once; else template) → pywebpush to all
   live subscriptions → `POST /nudges` (audit).
5. User taps notification → app opens on composer → logs → next hour's nudge acknowledges it.

**Morning special (first nudge ≥ 07:00):** built from yesterday's report `tomorrow_plan` —
"Plan says X, start with step 1."

## Flow 4 — Deep work declared

Log with deep-work chip (e.g. 120 min) → `data.block_minutes` → nudges silent until block end
+ 15 min → first nudge after asks for the outcome of the block, by name.

## Flow 5 — Midnight report (00:05, on Rig 2)

Agent pulls full IST-yesterday context → Ollama writes markdown (sections: shipped · blockers ·
numbers · streak & gates · tomorrow's plan ≤ 3 · one hard truth) → `POST /reports` → push
"Day N report ready" → phone: Reports tab renders it (sanitized). Ollama/Rig 2 failure →
retry once at 07:00; meanwhile Flow 7b already covered the gap.

## Flow 6 — Month close (1st, 00:25, on Rig 2)

Build archive for previous month (rendered md + verbatim raw logs/nudges/reports with all
timestamps + stats + counts) → `POST /archives/monthly` → `POST /purge {ym}` → API verifies
counts match exactly → deletes in one transaction → confirmation push "June archived: 412 logs,
28 reports". Any mismatch → 409, nothing deleted, alert push "archive verify failed".

## Flow 7 — Fallbacks (GitHub Actions)

a. **:20 past each hour (07:20–22:20):** if no nudge AND no log in 70 min → template push
   ("No coach this hour — Rig 2 looks offline. What moved since {last_log_time}? One line.").
b. **00:45:** yesterday has no report row → compute stats-only report (counts, expenses,
   streak) → store as `daily_fallback` + push.
c. **1st, 00:45:** archive row for last month missing → alert push "month-close didn't run".

## Flow 8 — Reading & exporting

Reports tab: list of daily reports (current + previous month) and monthly archives (forever).
Monthly → **Download PDF** (jsPDF, client-side: md content + stats + full timestamped log
appendix from `raw`). Yearly → pick year → compiled from that year's archives on device → PDF
with every month + complete timestamp appendix.

## Flow 9 — Edge cases

| Case | Behavior |
|---|---|
| Render cold start | agent/Actions retry ≤ 150 s; PWA shows "waking server…" on first request |
| Rig 2 off all day | fallback nudges keep cadence (generic); 00:45 stats report; LLM quality resumes when on |
| Push subscription expired (410) | pruned after 3 failures; app shows "notifications off?" banner when no live sub |
| Phone offline all day | logs queue locally; nudges still arrive (server-sent); sync on reconnect |
| Token rotated | old requests 401 → Settings prompts re-entry |
| Clock/timezone weirdness | server computes all IST boundaries; client never decides "today" |
| User logs at 23:30 (outside window) | logged normally; counted in that IST day; no nudge until 07:00 |
| Duplicate replay from offline queue | client UUID PK → second insert is a no-op 200 |

## Flow 10 — Future: sharing mode (designed, not built)

Invite code → Supabase Auth email OTP → JWT replaces static token in the PWA → same flows,
RLS-scoped per user; Rig 2 loops nudges per user with jitter + queue cap (Security §9).
