# Runbooks — Forge

Operational procedures. No secrets here — values live in the password manager,
`.env` files, Render env, and Actions secrets only (Security.md §5).

## R-1 · Rotate USER_TOKEN or AGENT_TOKEN

1. Generate: `py -c "import secrets;print(secrets.token_urlsafe(32))"` (do not echo into
   any shared terminal/chat).
2. USER_TOKEN: update Render env → redeploy happens automatically → paste the new token
   into the phone (PWA → Settings → Save token). Old token dies on deploy.
3. AGENT_TOKEN: update Render env **and** Rig 2 `agent/.env` **and** the Actions secret
   `AGENT_TOKEN` — all three before the next scheduled job.
4. Verify: old token → 401; phone can log; Rig 2 forced nudge run succeeds.

## R-2 · Rotate the VAPID keypair

1. On Rig 2: `python -m py_vapid --gen` in a scratch dir → derive the urlsafe-b64 private
   key + applicationServerKey (public).
2. Update: Rig 2 `agent/.env` `VAPID_PRIVATE_KEY` · Actions secret `VAPID_PRIVATE_KEY` ·
   `web/app.js` `CONFIG.VAPID_PUBLIC_KEY` (commit + push → Pages redeploys).
3. On the phone: open the PWA → Settings → **Enable notifications** again (old
   subscriptions die with the old key; one tap re-subscribes).
4. Verify: test push arrives; `GET /v1/push/subscriptions` (agent token) shows the new
   endpoint only.

## R-3 · Restore a backup locally

1. GitHub → Actions → backup run → download the `db-backup-*` artifact.
2. Decrypt + load into a scratch local Postgres:
   `openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:<BACKUP_PASSPHRASE> -in forge-*.sql.gz.enc | gunzip | psql <local scratch db url>`
3. Sanity: `select count(*) from logs;` matches expectations; RLS policies present
   (`\d+ logs` shows row security).

## R-4 · DATABASE_URL must be the forge_api role

The API must never connect as `postgres` (bypasses RLS — caught in P6). The session-pooler
URL's username decides the role:

- Correct: `postgresql://forge_api.<project-ref>:<forge_api password>@…pooler.supabase.com:5432/postgres`
- Wrong: `postgresql://postgres.<project-ref>:…` (superuser, `bypassrls = true`)

Check anytime: connect and `select current_user;` → must be `forge_api`.
Applies to Render env `DATABASE_URL` and local `api/.env`. `BACKUP_URL` (Actions) uses
`forge_backup.<project-ref>` the same way.

## R-5 · Re-register Rig 2 scheduled tasks

After moving the checkout or changing paths: edit `$py`/`$repo` at the top of
`agent/tasks/register_tasks.ps1` → run as admin. Verify in Task Scheduler: Forge Nudge
(hourly 07–22), Forge Report (00:05), Forge Report Retry (07:00), Forge Archive (1st 00:25),
all with "Wake to run" + "Run task as soon as possible after a scheduled start is missed".
