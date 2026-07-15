# POC — Forge risk spikes

Run these three spikes **before** the full build (ImplementationPlan P1). Each has a success
gate and a fallback so no dead end can eat the 16 h budget. Total budget: ~2.5 h.

## S1 — iOS Web Push end to end (the kill risk)

If this fails, the product concept fails — do it first.

Steps
1. `python -m py_vapid --gen` → keypair. Put public key in a 20-line test PWA
   (manifest + sw.js with `push` handler + subscribe button) in `/web`, deploy to GitHub Pages.
2. iPhone: open in Safari → Add to Home Screen → launch → allow notifications → copy the
   subscription JSON (display it on screen).
3. Rig 2: `pywebpush` script sends `{title, body}` to that subscription.

Success gate: notification appears on the **lock screen** with the app **closed**, delivered
within seconds. Also verify: phone on cellular (not just WiFi), and after a reboot.

Watch-outs: iOS < 16.4; notifications only work from the installed icon (never Safari tab);
iOS Focus modes silently swallow pushes — allowlist Forge in Focus settings.
Fallback if broken: re-add to Home Screen (subscriptions die if the PWA is re-installed);
check Settings → Notifications → Forge exists. There is no plan C on iOS + free — this must pass.

## S2 — Ollama nudge quality + latency on Rig 2

Steps
1. `ollama pull qwen2.5:7b-instruct` (Q4_K_M default).
2. Fixture context (copy from TechSpec §5, filled with a realistic fake day incl. a pending
   task and 3 prior nudges) → run the draft nudge prompt 10×, all four escalation levels.
3. Measure: total latency, tokens/s, RAM/VRAM headroom (`ollama ps` + Task Manager) **while the
   usual Docker demos are running** — this is the real Rig 2 condition (8 GB RAM box).

Success gates: p95 latency < 60 s · valid JSON `{title ≤ 40, body ≤ 220}` ≥ 8/10 runs ·
messages reference the fixture's actual log text (no hallucinated events) · hard-mode output is
blunt but lands inside the length caps · box stays usable.
Fallbacks: RAM-tight → `llama3.2:3b` (rerun gates); JSON flaky → grammar/format retry is already
designed (TechSpec §5), require ≥ 6/10 raw.

## S3 — Render cold start vs the agent

Steps
1. Deploy a stub FastAPI (`/healthz`, `/v1/context` returning fixture JSON, bearer check)
   to Render free via Docker.
2. Let it sleep 30+ min. Fire the agent's HTTP client (tenacity: 5 attempts, exp backoff
   2→60 s). Measure wake time. Repeat 3×.
3. From a GitHub Actions manual run, do the same (fallback path).

Success gates: agent survives every cold start within 150 s · zero manual retries · Actions job
completes < 3 min.
Fallback: cold starts worse than 150 s → add a 06:55 IST warm-ping to the agent schedule
(before the morning nudge) and accept slower fallback jobs; do NOT add a keep-alive pinger
(wasteful, against free-tier spirit).

## Exit

All three green → log results in Tracker.md (latency numbers, model chosen) → proceed to P2.
Any red after fallbacks → stop, redesign that leg before writing more code.
