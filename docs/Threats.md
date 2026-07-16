# Threat assessment — Forge (2026-07-16 audit)

Companion to Security.md. This is the "what can actually hurt me" pass, focused on the
owner's stated fears: someone using the GPU, data ingestion/exfiltration, and any inbound
threat to the home machine. Severity = likelihood × impact for THIS deployment (single user,
free tier, home GPU).

## CRITICAL — act before Rig 2 goes live

### T-1 · Ollama listens on 0.0.0.0:11434 (unauthenticated GPU access)
**Observed:** `netstat` shows Ollama bound to `0.0.0.0` and `[::]` — every network
interface, no auth, no token. Anyone who can reach the machine on port 11434 can run
arbitrary prompts on your GPU, pull/delete models, and read what the model is doing.

**Who can reach it today:**
- Any device on the same LAN/Wi-Fi (roommates, guests, a compromised IoT device).
- The whole internet **if** your router forwards 11434 or UPnP opened it, or on any public
  network (café, hostel, office) with no client-isolation.

**This is the "someone using my GPU / crypto-style abuse" risk, and it is real.** It is NOT
caused by Forge — Forge only ever calls `localhost` — but Forge's docs told you to run
Ollama, so the hardening lives here.

**Fix (do all three on Rig 2, and on Rig 1 now):**
1. Bind to localhost only. Set a system env var `OLLAMA_HOST=127.0.0.1:11434`, then restart
   Ollama (quit from the tray + relaunch, or restart the service). Re-check:
   `netstat -ano | findstr 11434` must show `127.0.0.1:11434`, not `0.0.0.0`.
   The agent talks to `http://localhost:11434` so nothing breaks.
2. Windows Defender Firewall: add an **inbound block** rule for TCP 11434 (belt-and-braces
   if the env var is ever lost). PowerShell (admin):
   `New-NetFirewallRule -DisplayName "Block Ollama inbound" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Block`
3. Never port-forward 11434. This is the same rule as Forge's invariant #2 (Rig 2 is
   pull-only) — no inbound path to the home machine, ever.

**Confirm the pull-only model holds:** Forge's whole design already means nothing on the
internet needs to reach Rig 2 — the agent makes *outbound* calls to Render. So there is
zero reason for 11434 (or any port) to be open inbound. Closing it costs you nothing.

## HIGH — fix during setup

### T-2 · DATABASE_URL connects as `postgres` (RLS bypassed)
Found in P6. The API's connection string uses the `postgres` superuser
(`rolbypassrls = true`), so Row-Level Security is not enforced for the API even though it's
enabled on every table. Single user today = no live exposure, but the moment a second user
exists (sharing mode) this is a full cross-tenant read/write hole. **Fix:** Runbooks R-4 —
swap the URL to the `forge_api` role in Render env and local `api/.env`; prove with
`phase-reports/spikes/p6_rls_crossread.py` → 7/7.

## MEDIUM — known, mitigated, worth understanding

### T-3 · Prompt injection via log text (LLM01)
Your own logs are the model's input. Today you're the only author, so this is
self-injection (low). It becomes real in sharing mode. **Mitigated:** log text is fenced in
`<logs>…</logs>`, the closing tag is escaped so user text can't break out, the system prompt
says the fenced block is untrusted data, and it's snapshot-tested. The LLM has **zero tools**
(it only emits text), so even a successful injection can't take actions — worst case is a
weird nudge. Keep it that way: never give the agent's LLM tool-use without a human-approval
gate.

### T-4 · LLM output rendered in the PWA (LLM02 / stored XSS)
Reports/nudges are model output shown in the app. **Mitigated:** rendered only through
`DOMPurify.sanitize(marked.parse(...))` — verified inert against `<img onerror>` and
`<script>` in-browser; push payloads are plain-text length-capped; CSP is `default-src
'self'` with scripts self-only, so even a bypass can't load external code. Residual: a
markdown link in a report could carry a `javascript:`/off-site URL — DOMPurify strips
`javascript:` by default; leave DOMPurify at defaults, don't add `ALLOW*` config.

### T-5 · USER_TOKEN in browser localStorage
Standard for a tokened PWA, but a token stealer / malicious extension / XSS could read it.
**Mitigated** by: CSP self-only (kills injected scripts), no third-party JS at all (vendored
libs), single-origin. **Residual:** it's a long-lived static token. Acceptable for v1
single-user; sharing mode replaces it with short-lived Supabase Auth JWTs (already the
designed swap point). Rotation is one tap (Runbooks R-1).

### T-6 · Agent trusts API responses without HTTPS pinning
`http.py` follows whatever `API_BASE` says. **Mitigated:** it's hard-set to the HTTPS Render
URL in `.env`; TLS authenticates the server. **Residual:** if someone edits `.env` to an
http:// or attacker URL the agent would send the AGENT_TOKEN there. Low (needs local file
access, which is game-over anyway). Optional hardening: assert `api_base.startswith("https://")`
at agent startup.

## LOW / accepted

- **Dependency CVEs:** `pip-audit` on the full env → **no known vulnerabilities** (2026-07-16).
  Re-run before each release; Dependabot could automate it (Someday).
- **Secrets in repo:** gitleaks CI + full-history scans clean; `.env`/`secrets/` gitignored;
  history was rewritten before going public. Ongoing risk is human paste error — the
  `--tb=line` habit (see incident in P0 report) exists because a traceback once printed a
  token; that set was rotated.
- **Rate-limit bypass:** X-Forwarded-For is client-spoofable, so the per-IP 401 burnout is
  defeatable by a determined attacker rotating the header. Accepted: the real wall is the
  256-bit constant-time token; the limiter only slows dumb scanners. Documented in code.
- **Render/Supabase/GitHub account takeover:** covered by 2FA (P0). The blast radius is the
  data, not the home network (pull-only). Backup (R-3) is the recovery path.
- **DoS on the free API:** anyone can hit `/healthz` and wake the dyno; no auth needed by
  design (it's the warmer). Worst case is Render free-tier hours burn faster; no data risk.

## The bottom line on your specific fears

| Your fear | Reality | What protects you |
|---|---|---|
| Someone using my GPU | **Real and open right now (T-1)** | Bind Ollama to localhost + firewall block — do it before Rig 2 |
| Data ingestion / someone reading my data | Low for v1 | RLS (once T-2 fixed) + single trust path + local-only LLM; data never leaves Supabase+Rig 2 |
| Inbound threat to my home PC | Structurally prevented | Pull-only design: no port forward, no tunnel, no inbound path — T-1 is the only thing that violated it, and closing 11434 restores it |
| Someone injecting commands via the app | Contained | Fenced prompts + tool-less LLM + DOMPurify + CSP |
