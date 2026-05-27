# Architecture Map

## Main Modules

- `src/mebelbot/config.py`
  Loads `.env`/environment settings and validates production readiness. Do not
  hardcode secrets or field IDs.

- `src/mebelbot/domain.py`
  Shared domain models and deep-link/source parsing.

- `src/mebelbot/content.py`
  Customer-facing bot copy and `BOT_CONTENT_JSON` override handling.

- `src/mebelbot/flow.py`
  Shared contact/order collection state machine. Messenger adapters should call
  into this instead of reimplementing flow rules.

- `src/mebelbot/storage.py`
  SQLite persistence for user sources, contacts, CRM submission status, and
  guided-flow state.

- `src/mebelbot/crm.py`
  CRM submission service, contact fingerprinting, duplicate protection, and retry
  orchestration.

- `src/mebelbot/bitrix.py`
  Bitrix24 webhook client, payload mapping, field validation, readback, and
  bounded retry behavior.

- `src/mebelbot/telegram_bot.py`
  Telegram aiogram adapter. Keep it thin: routing, Telegram UI, QR photo sending,
  and adapter-specific notification behavior only.

- `src/mebelbot/max_bot.py`
  Max webhook adapter and Max API client. Keep it thin: request validation,
  Max-specific update parsing, and sending text replies.

- `src/mebelbot/app.py`
  FastAPI ASGI app, webhook routers, startup webhook configuration, `/health`,
  `/ready`, and protected `/ops/status`.

- `src/mebelbot/qr.py`
  QR/deep-link generation, speaker CSV validation, and manifest creation.

- `src/mebelbot/__main__.py`
  CLI entrypoint for running Telegram polling, registering Max subscription,
  validating env, smoke testing Bitrix24, retrying failed CRM submissions, and
  printing local ops status.

## Boundaries

Shared business behavior belongs in `flow.py`, `crm.py`, `domain.py`,
`content.py`, or `storage.py`.

Telegram/Max adapters should remain transport/UI glue. Do not put CRM rules,
contact-state transitions, or source-attribution business logic directly into
adapter handlers unless the behavior is truly platform-specific.

## Runtime Shape

Telegram can run in polling mode with:

```bash
.venv/bin/mebelbot telegram
```

The ASGI app can serve Max and Telegram webhook endpoints:

```bash
.venv/bin/uvicorn mebelbot.app:app --host 0.0.0.0 --port 8000
```

HuggingFace Space Docker runtime uses port `7860`.
