-- RLS from day 1 (Schema.md §2, Security.md §3). API sets per request:
--   select set_config('app.user_id', '<uuid>', true);

alter table users enable row level security;
create policy p_user_users on users for all to forge_api
  using (id = current_setting('app.user_id')::uuid)
  with check (id = current_setting('app.user_id')::uuid);
create policy p_backup_users on users for select to forge_backup using (true);

do $$
declare t text;
begin
  foreach t in array array['settings','logs','tasks','nudges','reports','monthly_archives','push_subscriptions']
  loop
    execute format('alter table %I enable row level security', t);
    execute format(
      'create policy p_user_%1$s on %1$I for all to forge_api
         using (user_id = current_setting(''app.user_id'')::uuid)
         with check (user_id = current_setting(''app.user_id'')::uuid)', t);
    execute format('create policy p_backup_%1$s on %1$I for select to forge_backup using (true)', t);
  end loop;
end $$;
