-- Run ONCE in the Supabase SQL editor with real passwords (never committed).
-- These roles are the only DB principals: API (rw via RLS) + backup (ro). Schema.md §2.
create role forge_api login password 'REPLACE_ME';
create role forge_backup login password 'REPLACE_ME';
grant usage on schema public to forge_api, forge_backup;
alter default privileges in schema public grant select, insert, update, delete on tables to forge_api;
alter default privileges in schema public grant select on tables to forge_backup;
