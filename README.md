---
title: MebelBot
sdk: docker
emoji: 🛋️
colorFrom: blue
colorTo: green
app_port: 7860
---

# MebelBot

Telegram and Max chatbot with speaker attribution through deep links/QR codes. Bitrix24 CRM
submission is supported, but the current working mode is bot-first without Bitrix24 access.

## Demo direction

The `mvp/` folder contains a colleague's minimal Telegram-only demo. It is useful
as a reference for what the customer expects to see in the bot experience:

- a main menu with company information, catalog, order/contact form, and contacts;
- customer-facing furniture bureau copy rather than technical CRM wording;
- a guided order flow that asks for name, phone, and request details, then shows a
  confirmation screen before submission;
- catalog/category links and a clear way back to the main menu.

Do not run or copy `mvp/main.py` as production code. It is a Telegram-only demo with
placeholder URLs/contact details and in-memory state. The
production project should keep the shared Telegram/Max architecture and Bitrix24
submission flow, while adapting the visible demo UX to match this reference. See
[MVP_REVIEW.md](MVP_REVIEW.md) for the detailed gap analysis and demo acceptance
criteria.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill `.env` with bot tokens and public webhook host. Bitrix24 webhook URL and CRM field IDs
can stay empty until CRM access is available.

Validate the configured values before production use:

```bash
mebelbot validate-env
```

The validator reports missing values, placeholder defaults, invalid URLs, unsupported
database URLs, and malformed content links without printing secret values.

After adding real secrets, follow the checklist in [SECRET_TESTS.md](SECRET_TESTS.md).

## Current CRM Mode

There is no Bitrix24 portal access yet, so the bot should be developed and demoed without
CRM submission as a required dependency. Telegram can run with CRM disabled; collected
contact/order data is still stored in SQLite. Bitrix24 setup, field validation, smoke tests,
and CRM retry operations are deferred until real portal credentials and field mappings are
provided.

Bot copy can be overridden without code changes through `BOT_CONTENT_JSON`. Supported
keys are the fields in `BotContent`, including menu labels, welcome/about/catalog/
contacts text, order prompts, confirmation/edit/cancel text, validation messages,
CRM success text, and temporary CRM error text.

The customer-facing flow now opens with the furniture bureau menu and supports a
guided order form in both Telegram and Max: name, phone, request details, then
confirmation with submit, edit, or cancel actions. When Bitrix24 is later enabled,
request details will be included in the configured Bitrix24 comment field.

Contact submissions are stored in SQLite with a contact fingerprint and status. Once
Bitrix24 is enabled, temporary CRM failures are retried before the contact is marked as
failed, and duplicate messages with the same channel, user, phone, and source reuse the
existing CRM result.

## Run Telegram bot

```bash
mebelbot telegram
```

## Run Max webhook server

```bash
uvicorn mebelbot.app:app --reload --host 0.0.0.0 --port 8000
```

Webhook endpoint:

```text
POST /webhooks/max
```

Max webhook requests must include `X-Max-Bot-Api-Secret` equal to `WEBHOOK_SECRET`.
For production Max requires an HTTPS endpoint on port 443 with a trusted TLS certificate.

Register the webhook subscription after `WEBHOOK_HOST` is set to your public HTTPS host:

```bash
mebelbot max-subscribe
```

The subscription listens to:

```text
bot_started,message_created
```

`bot_started` is required for Max deep links because the `start` payload is delivered in
the webhook update payload.

## Deploy on HuggingFace Spaces

The files in `deploy guides/` describe a free HuggingFace + Cloudflare Worker pattern for
simple `telebot` projects. This project uses `aiogram` and FastAPI, so deploy the ASGI app
from the included `Dockerfile` instead of copying `main.py` snippets from the guide.

After every project change that should be deployed, commit it and push to both remotes:

```bash
git push origin main
git push huggingface main
```

Current remotes:

```text
GitHub: https://github.com/jxlsij/mebelBot-deploy
HuggingFace Space: https://huggingface.co/spaces/amiasayedau/mebelbot-deploy
Public app URL: https://amiasayedau-mebelbot-deploy.hf.space
```

Create a HuggingFace Space with Docker runtime and push the repository. The container starts:

```bash
uvicorn mebelbot.app:app --host 0.0.0.0 --port 7860
```

Set these Space secrets/variables:

```text
TELEGRAM_BOT_TOKEN=...
WEBHOOK_HOST=https://amiasayedau-mebelbot-deploy.hf.space
DATABASE_URL=sqlite:///data/mebelbot.sqlite3
```

If Telegram API calls from HuggingFace are blocked, create the Cloudflare Worker from
`deploy guides/deploy_guide_ai.md` and set:

```text
TELEGRAM_API_BASE=https://your-worker.workers.dev
```

For compatibility with the original guide, `TELEGRAM_API_URL` in the
`https://your-worker.workers.dev/bot{0}/{1}` format is also accepted.

Recommended Telegram webhook hardening:

```text
TELEGRAM_WEBHOOK_SECRET=long-random-secret
```

When `WEBHOOK_HOST` and `TELEGRAM_BOT_TOKEN` are set, the ASGI app registers:

```text
POST /webhooks/telegram
```

Max can run from the same ASGI app if these values are also configured:

```text
MAX_BOT_TOKEN=...
WEBHOOK_SECRET=long-random-secret
```

Then register the Max subscription:

```bash
mebelbot max-subscribe
```

Max production webhooks require HTTPS on port 443 with a trusted TLS certificate. If the
target host cannot satisfy that requirement, use the HuggingFace deployment for Telegram
only and deploy Max behind a production HTTPS endpoint separately.

Before pushing to Git, run:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

## Retry failed CRM submissions

If Bitrix24 was unavailable, failed submissions stay in SQLite and can be retried by an
operator:

```bash
mebelbot retry-failed-crm
```

To process only a small batch:

```bash
mebelbot retry-failed-crm --limit 10
```

## Verify Bitrix24 integration

Deferred until Bitrix24 access is available.

After `.env` contains the real Bitrix24 webhook URL, entity type, and CRM field codes,
create a disposable test CRM item and read it back to prove that the speaker/source field
is mapped correctly:

```bash
mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

The command uses `BITRIX24_ENTITY` to choose lead or deal, then checks that
`BITRIX24_SOURCE_FIELD` contains the same source code that was sent.

Before creating a smoke-test CRM item, validate that the configured field mapping exists
on the selected Bitrix24 entity:

```bash
mebelbot bitrix-validate-fields
```

If the command reports missing fields, update `BITRIX24_ENTITY` and the
`BITRIX24_*_FIELD` values in `.env` before running the smoke test.

## Generate speaker QR codes

Create `data/speakers.csv`:

```csv
code,name
ivanov,Иван Иванов
petrova,Анна Петрова
```

Then run it with the real public bot usernames, without placeholder values:

```bash
mebelbot-qr --speakers data/speakers.csv --telegram-username mebel_real_bot --max-username mebel_real_bot --out data/qr
```

If `TELEGRAM_BOT_USERNAME` and `MAX_BOT_USERNAME` are set in `.env`, the usernames can
be omitted:

```bash
mebelbot-qr --speakers data/speakers.csv --out data/qr
```

The command prints deep links, writes QR PNG files for both channels, and creates
`data/qr/manifest.csv` with every speaker code, display name, Telegram link, Max link,
and generated PNG path. Speaker codes may contain only letters, numbers, `_`, and `-`.

Before sending QR files to speakers, manually verify each row from the manifest:

1. Open the Telegram and Max links for one speaker at a time.
2. Start the bot and submit a test request through the guided form.
3. Confirm in Bitrix24 that `BITRIX24_SOURCE_FIELD` contains the exact `code` from the manifest.
4. Repeat for every speaker/source row, then archive or delete the test CRM items.
