# Rules — Forge repo (house rules for every session)

Derived from Blueprint v2.1 Ch. 6A + Ch. 12. Violations are review-blockers.

## R1 — Ownership split (adapted Ch. 6A)

Forge is a **tool** (Rule-2 territory): scaffolding, routes, PWA plumbing, YAML, tests →
generate/delegate freely. Hand-written by Sahil only, never delegated:
- `/agent/prompts/*` (the coach's voice IS the product)
- the purge-invariant logic in `/purge`
- `Security.md` decisions
Nothing merges unexplained: self-review every diff; commit messages state **why**, written by
Sahil (Ch. 6A R3).

## R2 — Scope freeze

PRD "Won't" list is law. Any new idea mid-session → one line in Tracker.md → Someday, then back
to the phase task (Ch. 12: "a new project idea while a project is unfinished = the avoidance
pattern"). Forge work must never displace Project 1 hours: hard cap 16 h to v1, then Forge only
gets maintenance minutes.

## R3 — Security invariants (never regress; CI-gated where possible)

1. Verify-before-purge (Schema §5) — no deletion without a count-verified archive.
2. Rig 2 is pull-only — no inbound tunnel/port-forward ever lands in this repo.
3. Every LLM-rendered surface goes through DOMPurify; push payloads plain text + length caps.
4. No secret in repo/client (gitleaks CI); tokens only in Authorization headers.
5. RLS stays enabled on all tables; new tables ship with `user_id` + policy in the same migration.
6. User/log text is untrusted input everywhere: length caps, fenced in prompts, never eval'd.

## R4 — Code style

Python 3.12, fully typed, Pydantic v2 models at boundaries, async end-to-end in API; ruff
(format + lint) is the only style authority. Small modules over clever abstractions; no ORM
magic beyond SQLAlchemy core patterns already in the repo. Frontend: vanilla JS, no build step,
no framework, vendored libs only (CSP `self`). Plain SQL migrations, numbered, never edited
after merge.

## R5 — Testing bar

CI (ruff + pytest + gitleaks) must be green to merge. Table-driven tests required for:
suppression matrix, escalation compute, purge invariant, auth scopes. Prompt-builder snapshot
tests guard against silent context regressions. No mocking Ollama quality in CI — LLM output
handling is tested via schema-validation paths (valid/invalid/timeout).

## R6 — Timezone & data discipline

All "day" math via `core/time.py` (IST) — never inline. DB is UTC. Client never decides what
day it is. Every write path is idempotent or uniquely keyed (client UUIDs, `unique(user_id,
date, kind)`).

## R7 — Session protocol

Start: read the current phase in ImplementationPlan → its DoD. End (mandatory): tests
green · deployable commit pushed · Tracker.md updated (date, phase, shipped, blockers, minutes)
· next session's single task written down. A session with no shipped artifact gets logged as a
miss (Ch. 12 rule — misses are data, not shame).

## R8 — When stuck

20-minute research cap (Ch. 12), then: reproduce in a failing test, or write the limitation
into Tracker.md → Blockers and move to the next task. Two consecutive stuck sessions on the
same item → scope-cut discussion (ImplementationPlan cut list), never a rewrite.
