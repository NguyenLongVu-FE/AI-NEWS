# Deploy & Rollback Runbook (Phase 3)

## 1. Required Vercel Environment Variables

Set all values in Vercel Project Settings > Environment Variables:

- `TELEGRAM_TOKEN`
- `TELEGRAM_BOT_TOKEN` (compatibility alias used by current runtime code)
- `GEMINI_API_KEY`
- `GOOGLE_CREDENTIALS_JSON`
- `GOOGLE_SHEET_ID`
- `TELEGRAM_WEBHOOK_SECRET`
- `ADMIN_TELEGRAM_ID`

Notes:
- Keep credentials in Vercel only. Do not commit secrets.
- `GOOGLE_CREDENTIALS_JSON` must be a single-line JSON string.

## 2. Branching and Deploy Flow

- Work on a **feature branch**.
- Open PR to **main branch**.
- Merge to `main` after CI is green.
- Vercel auto-deploys from `main`.

## 3. Post-Deploy Verification

Use default Vercel domain (no custom domain required), for example:

`https://infosaver-bot.vercel.app`

Run:

```bash
BASE_URL=https://infosaver-bot.vercel.app python scripts/deploy_checks.py --base-url "$BASE_URL"
```

Expected:
- Health check passes (`/api/health` or `/health`)
- Webhook secret guard passes (`/api/webhook` or `/webhook`)

## 4. Telegram Webhook Setup

Register webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://infosaver-bot.vercel.app/api/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Validate webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo"
```

Both `setWebhook` and `getWebhookInfo` must show the expected target URL and no pending configuration errors.

## 5. Monitoring

Use **Vercel dashboard** for:
- request volume
- function duration
- error rate
- function logs

Admin alerts are delivered through Telegram when error threshold logic is triggered in app middleware.

## 6. Weekly Backup

Cron schedule in `vercel.json`:
- daily digest: `/api/cron/digest`
- weekly backup (Monday 09:00 ICT): `/api/cron/backup`

Digest endpoint is intentionally disabled in topic-first mode and returns:
`{"enabled": false, "reason": "digest_disabled_in_topic_model", ...}`

## 7. Topic Sheet Operations

Command family:
- `/topics`
- `/filter @topic #keyword`

Behavior:
- Main data is stored in topic sheets only.
- Sheets follow fixed naming format: `TOPIC_<slug>`.
- Each record belongs to exactly one topic sheet.
- ID is global across all topic sheets.
- `DASHBOARD` sheet is rebuilt automatically after add/edit/delete operations and summarizes topic health.

Recovery:
- If commands return not-found for a known ID, inspect sheet data and verify ID uniqueness.

## 8. Rollback Procedure

If production breaks:

1. Open Vercel dashboard.
2. Go to Deployments.
3. Select last known good deploy.
4. Trigger **Rollback**.
5. Re-run deploy checks and `getWebhookInfo`.

This is the emergency path; no immediate git revert is required for first response.
