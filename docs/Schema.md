# Schema — Forge v1 (Postgres / Supabase)

Migration files: `api/migrations/00X_*.sql`, applied by `scripts/migrate.py` (plain SQL, ordered).
UTC `timestamptz` everywhere; IST math happens in app code. Every table carries `user_id` (PRD §7).

## 1. DDL

```sql
-- 001_init.sql
create extension if not exists pgcrypto;

create table users (
  id           uuid primary key default gen_random_uuid(),
  email        text unique not null,
  display_name text,
  created_at   timestamptz not null default now()
);

create table settings (
  user_id                uuid primary key references users(id) on delete cascade,
  tz                     text not null default 'Asia/Kolkata',
  active_start           smallint not null default 7,
  active_end             smallint not null default 22,
  nudge_min_gap_min      smallint not null default 50,
  suppress_after_log_min smallint not null default 25,
  hard_mode_after_hours  smallint not null default 4,
  plan_day_anchor        date,                -- Day N/84 counter start
  updated_at             timestamptz not null default now()
);

create table logs (
  id         uuid primary key,                -- client-generated (offline idempotency)
  user_id    uuid not null references users(id) on delete cascade,
  ts         timestamptz not null default now(),
  type       text not null default 'checkin'
             check (type in ('checkin','task','expense','fitness','habit')),
  text       text not null check (char_length(text) <= 4000),
  data       jsonb not null default '{}'::jsonb,  -- {amount, habit, block_minutes, ...}
  source     text not null default 'pwa',
  created_at timestamptz not null default now()
);
create index logs_user_ts on logs (user_id, ts desc);

create table tasks (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users(id) on delete cascade,
  title         text not null check (char_length(title) <= 300),
  status        text not null default 'pending' check (status in ('pending','done','dropped')),
  origin_log_id uuid references logs(id) on delete set null,
  created_ts    timestamptz not null default now(),
  closed_ts     timestamptz
);
create index tasks_user_status on tasks (user_id, status);

create table nudges (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  ts         timestamptz not null default now(),
  kind       text not null check (kind in ('hourly','fallback','report_ready')),
  title      text not null,
  body       text not null,
  escalation smallint not null default 0,
  model      text,
  latency_ms integer
);
create index nudges_user_ts on nudges (user_id, ts desc);

create table reports (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  date       date not null,                    -- IST day it covers
  kind       text not null check (kind in ('daily','daily_fallback')),
  md         text not null,
  stats      jsonb not null default '{}'::jsonb,
  model      text,
  created_ts timestamptz not null default now(),
  unique (user_id, date, kind)
);

create table monthly_archives (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  ym         char(7) not null,                 -- '2026-07'
  md         text not null,                    -- rendered month report
  raw        jsonb not null,                   -- verbatim {logs[], nudges[], reports[]} with ALL timestamps
  stats      jsonb not null,
  counts     jsonb not null,                   -- {"logs":n,"nudges":n,"reports":n} for purge verification
  created_ts timestamptz not null default now(),
  unique (user_id, ym)
);

create table push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  endpoint   text not null unique,
  p256dh     text not null,
  auth       text not null,
  ua         text,
  created_ts timestamptz not null default now(),
  last_ok_ts timestamptz,
  failures   smallint not null default 0
);
```

## 2. Roles & RLS (day 1, multi-user-ready)

```sql
-- 002_rls.sql
create role forge_api login password :'FORGE_API_PW';       -- API service role (no bypassrls)
create role forge_backup login password :'FORGE_BACKUP_PW'; -- read-only, backups only
grant select, insert, update, delete on all tables in schema public to forge_api;
grant select on all tables in schema public to forge_backup;

alter table users            enable row level security;
alter table settings         enable row level security;
alter table logs             enable row level security;
alter table tasks            enable row level security;
alter table nudges           enable row level security;
alter table reports          enable row level security;
alter table monthly_archives enable row level security;
alter table push_subscriptions enable row level security;

-- API sets per-request:  select set_config('app.user_id', '<uuid>', true);
create policy p_logs on logs for all to forge_api
  using (user_id = current_setting('app.user_id')::uuid)
  with check (user_id = current_setting('app.user_id')::uuid);
-- (identical policy on every user_id table; users: id = setting)
create policy p_backup_read on logs for select to forge_backup using (true);
-- (repeat read policy per table)
-- Supabase PostgREST roles (anon, authenticated): NO policies → deny by default.
```

Seed (003): insert Sahil's user row + settings; `plan_day_anchor = '2026-07-15'`.

## 3. `data` jsonb conventions

| type | keys |
|---|---|
| checkin | `block_minutes` (declared deep-work) |
| task | `task_id` (link after task creation) |
| expense | `amount` (number, INR), `category?` |
| fitness | `kind?`, `duration_min?` |
| habit | `habit` (name), `done` (bool) |

Unknown keys allowed (forward-compatible); API validates known keys' types.

## 4. Retention model

- Live DB holds the **current month** and the **previous month until archived** (1st, 00:25 IST).
- `monthly_archives` rows are permanent and self-sufficient: `raw` contains every log, nudge and
  daily report verbatim with timestamps; `md` is the human month report; yearly view is compiled
  on demand from 12 archive rows (never stored).
- Purge scope for month M: rows with ts/date in [M 00:00 IST, M+1 00:00 IST) in `logs`, `nudges`,
  `reports`. Tasks are NOT purged (open loops persist); closed tasks older than 60 d may be pruned
  after appearing in an archive.

## 5. Purge invariant (sacred — test-gated, never edit casually)

1. Agent builds archive for M and `POST /archives/monthly` → row committed with `counts` and
   min/max ts per table.
2. `POST /purge {ym}`: API re-counts live rows in M's window; **counts must equal archive
   `counts` exactly**, else 409 + alert push, nothing deleted.
3. Delete in one transaction; deleted-row counts must equal archive counts, else rollback + alert.
4. Fallback-report job on the 1st independently verifies the archive row exists.

No verified archive → no deletion, ever. Violation count is a PRD success metric (target 0).

## 6. Size math

~15 logs/day ≈ 2 KB → month ≈ 1 MB incl. nudges/reports; archive jsonb ≈ 1–2 MB/month.
Years of headroom in Supabase's 500 MB.
