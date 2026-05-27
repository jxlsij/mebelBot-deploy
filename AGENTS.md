# MebelBot Agent Notes

## Project

MebelBot is a Python chatbot project for Telegram and Max with shared business logic,
speaker attribution through deep links/QR codes, and Bitrix24 CRM submission.

The implementation is driven by `SPEC.md` and tracked in `TASKS.md`.
The `mvp/` folder contains a colleague's minimal Telegram demo. Use it as a
customer-facing UX/content reference, not as production code.

## Structure

- `src/mebelbot/config.py` loads environment configuration from `.env`.
- `src/mebelbot/domain.py` contains shared domain models and source parsing.
- `src/mebelbot/flow.py` contains shared contact collection and CRM submission flow.
- `src/mebelbot/storage.py` contains SQLite persistence for sources and CRM submission state.
- `src/mebelbot/bitrix.py` contains the Bitrix24 webhook client with retry handling.
- `src/mebelbot/telegram_bot.py` contains the Telegram aiogram adapter.
- `src/mebelbot/max_bot.py` contains the Max webhook adapter and API client.
- `src/mebelbot/qr.py` generates Telegram/Max deep links and QR PNG files.
- `tests/` contains pytest coverage for domain logic, CRM flow, Max contract, QR, and storage.

## Commands

Use the local virtualenv:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Run Telegram polling:

```bash
.venv/bin/mebelbot telegram
```

Run Max webhook server:

```bash
.venv/bin/uvicorn mebelbot.app:app --reload --host 0.0.0.0 --port 8000
```

Register Max webhook subscription:

```bash
.venv/bin/mebelbot max-subscribe
```

Generate QR codes:

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --telegram-username your_tg_bot --max-username your_max_bot --out data/qr
```

## Environment

Do not hardcode credentials. Use `.env` based on `.env.example`.

Important variables:

- `TELEGRAM_BOT_TOKEN`
- `MAX_BOT_TOKEN`
- `BITRIX24_WEBHOOK_URL`
- `DATABASE_URL`
- `WEBHOOK_HOST`
- `WEBHOOK_SECRET`
- `BITRIX24_SOURCE_FIELD`

## Current Work

Before starting a task, read `TASKS.md`.

After every project change that should go live, commit and push to both deployment
remotes:

```bash
git push origin main
git push huggingface main
```

Current next task at initialization time:

- Bring the customer-facing demo to the shape shown in `mvp/main.py`: main menu,
  "About", "Catalog", "Contacts", and a guided order/contact form with confirmation.

## Notes

- Keep messenger adapters thin; shared behavior belongs in `flow.py`, `crm.py`, `domain.py`, or `storage.py`.
- Max production webhooks require HTTPS on port 443 and a trusted TLS certificate.
- CRM submissions use a contact fingerprint to avoid duplicate Bitrix24 records.
- The MVP is Telegram-only, stores state in memory, uses placeholder catalog/contact
  data, and contains a hardcoded bot token. Do not copy those parts. Port only the
  useful product shape into the shared Telegram/Max implementation.
- The current production code is technically broader than the MVP, but the customer
  demo should be friendlier: menu sections, furniture-bureau copy, category links,
  and step-by-step contact/order collection.
- After code changes, run both pytest and ruff.
- `deploy guides/` contains a free HuggingFace + Cloudflare Worker deployment guide for
  simple `telebot` projects. Treat it as deployment reference only: this project uses
  `aiogram` and FastAPI, so production deployment needs an ASGI Dockerfile/start command
  instead of copying the `main.py`/`telebot` snippets directly.
