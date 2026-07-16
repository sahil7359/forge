# Forge

Personal accountability and grind tracker.
iPhone PWA · hourly local-LLM coach nudges · midnight reports · free-tier hosting end to end.

**Owner:** Sahil Chakraborty · contact: help.sahil.gob@gmail.com · single user v1
(multi-user-ready) · timezone Asia/Kolkata (IST)

## Documents

| Doc | Purpose |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements: features, priorities, non-goals, success metrics |
| [docs/TechSpec.md](docs/TechSpec.md) | Stack, repo layout, API spec, jobs/crons, prompts, error handling |
| [docs/AppFlow.md](docs/AppFlow.md) | Every user journey and system flow, incl. edge cases |
| [docs/Design.md](docs/Design.md) | UI design system, screens, iOS PWA specifics |
| [docs/Schema.md](docs/Schema.md) | Full DDL, indexes, RLS, retention + purge invariant |
| [docs/Security.md](docs/Security.md) | Threat model, layered controls, agentic-OWASP mapping, sharing mode |
| [docs/POC.md](docs/POC.md) | Three risk spikes to run before the full build |
| [docs/ImplementationPlan.md](docs/ImplementationPlan.md) | Phased plan with commands, budgets, DoD |
| [docs/Tracker.md](docs/Tracker.md) | Living tracker: status, session log, decisions, parked ideas |
| [docs/Rules.md](docs/Rules.md) | Engineering + workflow rules for this repo |

## Architecture in one paragraph

The PWA (GitHub Pages, free) installs on the iPhone via Safari → Add to Home Screen and talks
HTTPS + bearer token to a FastAPI service (Render free) backed by Supabase Postgres (free).
Rig 2 (home Windows PC, RTX 2060 Super) runs all intelligence via Task Scheduler: hourly it pulls
context and asks local Ollama (qwen2.5:7b) for a personalised coach nudge pushed to the phone;
at 00:05 IST it writes the daily report + tomorrow's plan; on the 1st it archives the previous
month (every log, every timestamp) and only then purges raw rows. GitHub Actions is the fallback
layer (template reminder, stats-only report, archive check) plus CI, Pages deploy, weekly backup.
Rig 2 is pull-only: nothing on the internet can reach the home network.

## Ground rules

Forge is a **tool**, not another side project. Keep boilerplate cheap, timebox per
ImplementationPlan (~16 h to v1), park every new idea in Tracker.md → Someday.
