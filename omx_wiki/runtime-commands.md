# Runtime Commands

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Validation

```bash
.venv/bin/mebelbot validate-env
.venv/bin/pytest -q
.venv/bin/ruff check .
```

The test suite was last observed passing with `62 passed` after the production
ops-status work.

## Run Telegram Polling

```bash
.venv/bin/mebelbot telegram
```

## Run ASGI App

```bash
.venv/bin/uvicorn mebelbot.app:app --reload --host 0.0.0.0 --port 8000
```

Production Docker/HuggingFace command:

```bash
uvicorn mebelbot.app:app --host 0.0.0.0 --port 7860
```

## Register Max Subscription

```bash
.venv/bin/mebelbot max-subscribe
```

Only run this after final production host and Max token/secret are configured.
Max production webhooks require a public HTTPS endpoint on port 443 with a
trusted TLS certificate.

## Bitrix24 Checks

```bash
.venv/bin/mebelbot bitrix-validate-fields
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

## Retry Failed CRM Submissions

```bash
.venv/bin/mebelbot retry-failed-crm
.venv/bin/mebelbot retry-failed-crm --limit 10
```

## Operator Status

Local CLI:

```bash
.venv/bin/mebelbot ops-status
```

HTTP endpoints:

```bash
curl https://your-host.example/health
curl https://your-host.example/ready
curl -H "X-MebelBot-Admin-Secret: $OPS_STATUS_SECRET" https://your-host.example/ops/status
```

`/ops/status` is disabled unless `OPS_STATUS_SECRET` is set.

## QR Generation

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --telegram-username TELEGRAM_USERNAME --max-username MAX_USERNAME --out data/qr
```

If `TELEGRAM_BOT_USERNAME` and `MAX_BOT_USERNAME` are configured:

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --out data/qr
```

## Git/Deploy Rule

After every committed project change that should go live:

```bash
git push origin main
git push huggingface main
```
