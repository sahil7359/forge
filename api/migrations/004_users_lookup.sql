-- Bootstrap fix: forge_api must resolve token -> user BEFORE app.user_id exists
-- (002's p_user_users requires the setting, so the first lookup can never succeed).
-- Lookup is SELECT-only; user writes remain restricted by p_user_users (002).
-- v2: the same policy serves JWT-sub -> user resolution.
create policy p_api_users_lookup on users for select to forge_api using (true);
