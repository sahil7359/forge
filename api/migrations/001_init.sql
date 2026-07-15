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
  plan_day_anchor        date,
  updated_at             timestamptz not null default now()
);

create table logs (
  id         uuid primary key,
  user_id    uuid not null references users(id) on delete cascade,
  ts         timestamptz not null default now(),
  type       text not null default 'checkin'
             check (type in ('checkin','task','expense','fitness','habit')),
  text       text not null check (char_length(text) <= 4000),
  data       jsonb not null default '{}'::jsonb,
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
  date       date not null,
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
  ym         char(7) not null,
  md         text not null,
  raw        jsonb not null,
  stats      jsonb not null,
  counts     jsonb not null,
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
