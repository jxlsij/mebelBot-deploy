# Operations And Monitoring

## Health And Readiness

`/health` is a lightweight uptime check:

```bash
curl https://your-host.example/health
```

`/ready` touches SQLite and confirms runtime readiness:

```bash
curl https://your-host.example/ready
```

## Protected Ops Status

Set:

```text
OPS_STATUS_SECRET=long-random-operator-secret
```

Then query:

```bash
curl -H "X-MebelBot-Admin-Secret: $OPS_STATUS_SECRET" https://your-host.example/ops/status
```

The endpoint returns:

- whether Telegram webhook is enabled;
- whether Max webhook is enabled;
- whether Bitrix24 is configured;
- CRM submission counts by `pending`, `sent`, and `failed`.

It does not expose tokens, webhook URLs, phone numbers, contacts, or Bitrix
payloads.

If `OPS_STATUS_SECRET` is empty, `/ops/status` returns 404.

## Local Operator Status

```bash
.venv/bin/mebelbot ops-status
```

This prints local status, database path, integration flags, and CRM submission
counts.

During one local check, the current SQLite DB had 3 failed CRM submissions. That
is expected to be visible through ops status and can be retried after CRM is
configured.

## Failed CRM Retry

```bash
.venv/bin/mebelbot retry-failed-crm
.venv/bin/mebelbot retry-failed-crm --limit 10
```

If failed count stays above zero after retry, inspect logs and Bitrix24
connectivity/settings.

## Logging

HTTPX logging is lowered to warning to avoid noisy logs and to reduce risk of
printing sensitive webhook URLs. CLI errors are concise and should avoid
revealing secret values.
