# Security Best Practices Report

## Executive Summary

Audit scope: Python/FastAPI/aiogram/httpx/SQLite project, with focus on secrets, Telegram/Max webhook handling, Bitrix24 outbound integration, SQL injection risk, and unauthenticated endpoints.

No hardcoded production tokens were found in tracked source files. `.env` is ignored by Git, and `.env.example` contains placeholders only. SQL injection risk is currently low because runtime queries use parameter binding; the only dynamic SQL found is internal schema migration code using hardcoded table/column names.

Remediation status: all findings below were fixed after the audit. The project now requires a Telegram webhook secret for ASGI webhook mode, disables FastAPI docs by default, limits webhook request bodies, validates Max webhook payloads through Pydantic models, compares webhook secrets with `secrets.compare_digest()`, and applies app-level host validation when a webhook host is configured.

## High Severity

### SBP-001: Telegram webhook accepts unauthenticated requests when `TELEGRAM_WEBHOOK_SECRET` is empty

- Rule ID: FASTAPI-AUTH-001 / webhook verification
- Severity: High
- Location: `src/mebelbot/telegram_bot.py`, `telegram_webhook`, lines 201-214; `src/mebelbot/config.py`, `validate_environment`, lines 170-175; `README.md`, lines 178-188
- Evidence:

```python
if (
    settings.telegram_webhook_secret
    and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
):
    raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
```

`validate_environment()` only warns when `TELEGRAM_WEBHOOK_SECRET` is present but short; it does not require the secret for webhook deployments. README describes it as "Recommended Telegram webhook hardening" rather than required.

- Impact: If the public `/webhooks/telegram` endpoint is deployed with only `TELEGRAM_BOT_TOKEN` and `WEBHOOK_HOST`, anyone who can reach the URL can POST forged Telegram updates. This can trigger bot replies, create local contact records, and attempt CRM submissions.
- Fix: Require `TELEGRAM_WEBHOOK_SECRET` whenever Telegram webhook mode is enabled, and reject all webhook requests without a valid `X-Telegram-Bot-Api-Secret-Token` header. Treat polling mode separately.
- Mitigation: Until code is changed, ensure production env always sets a long random `TELEGRAM_WEBHOOK_SECRET`; optionally restrict `/webhooks/telegram` at the reverse proxy if possible.
- False positive notes: If Telegram is only run in polling mode and `/webhooks/telegram` is not exposed, impact is not present for that deployment. The ASGI app currently includes the route whenever `TELEGRAM_BOT_TOKEN` is set.
- Status: Fixed in `src/mebelbot/config.py` and `src/mebelbot/telegram_bot.py`.

## Medium Severity

### SBP-002: FastAPI OpenAPI/docs endpoints are enabled by default in production

- Rule ID: FASTAPI-OPENAPI-001
- Severity: Medium
- Location: `src/mebelbot/app.py`, `create_app`, line 43
- Evidence:

```python
app = FastAPI(title="MebelBot", lifespan=lifespan)
```

No `docs_url=None`, `redoc_url=None`, or `openapi_url=None` is configured for production.

- Impact: Public `/docs`, `/redoc`, and `/openapi.json` disclose endpoint paths, request schemas, and operational details. This makes webhook probing and abuse easier.
- Fix: Add production settings to disable docs/openapi by default, or protect them behind auth/network allowlist.
- Mitigation: Block `/docs`, `/redoc`, and `/openapi.json` at the edge until app-level config exists.
- False positive notes: Docs exposure may be acceptable for a public API, but this app is primarily a bot webhook receiver, so public docs provide little user value.
- Status: Fixed in `src/mebelbot/app.py`; docs are disabled unless `ENABLE_API_DOCS=true`.

### SBP-003: Webhook JSON bodies are loaded without an app-level size limit

- Rule ID: input validation / request resource limits
- Severity: Medium
- Location: `src/mebelbot/telegram_bot.py`, `telegram_webhook`, line 212; `src/mebelbot/max_bot.py`, `max_webhook`, line 148
- Evidence:

```python
update = Update.model_validate(await request.json(), context={"bot": bot})
```

```python
update = await request.json()
```

- Impact: A public attacker can send very large JSON bodies to webhook endpoints. Even if auth rejects some requests, Telegram auth is optional per SBP-001 and Max still parses after header verification. Large payloads can consume memory/CPU and degrade the process.
- Fix: Add a small request-size limit middleware or check `Content-Length` before `request.json()`. Telegram/Max updates should fit comfortably under a conservative limit such as 256 KiB or 1 MiB.
- Mitigation: Configure reverse proxy/CDN/request gateway body-size limits.
- False positive notes: Infrastructure may already enforce a request size cap, but no app-level limit is visible in the repo.
- Status: Fixed in `src/mebelbot/app.py` with `WEBHOOK_MAX_BODY_BYTES`.

### SBP-004: Max webhook body is accepted as an untyped dict with minimal schema validation

- Rule ID: input validation
- Severity: Medium
- Location: `src/mebelbot/max_bot.py`, `extract_text`, lines 24-27; `extract_user_id`, lines 30-37; `max_webhook`, lines 148-163
- Evidence:

```python
update = await request.json()
text = extract_text(update)
user_id = extract_user_id(update)
```

The code accepts either nested `message.sender.user_id`, `message.user_id`, or top-level `user_id`, then proceeds with state mutation and outbound bot replies.

- Impact: If the Max webhook secret leaks or is misconfigured, an attacker can spoof arbitrary user IDs and payload shapes more easily because there is no strict update model, timestamp validation, or update-type schema boundary.
- Fix: Add Pydantic models for expected Max update types (`bot_started`, `message_created`) and reject unknown shapes with 400. Consider validating timestamp freshness if Max provides reliable timestamps.
- Mitigation: Keep `WEBHOOK_SECRET` long and random, rotate it if exposed, and monitor unexpected update shapes.
- False positive notes: The current secret header is a meaningful primary control; this finding is about defense-in-depth after auth.
- Status: Fixed in `src/mebelbot/max_bot.py`.

## Low Severity

### SBP-005: Webhook secret comparisons use normal string equality

- Rule ID: secret comparison hardening
- Severity: Low
- Location: `src/mebelbot/telegram_bot.py`, lines 206-210; `src/mebelbot/max_bot.py`, lines 145-146
- Evidence:

```python
x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
```

```python
x_max_bot_api_secret != settings.webhook_secret
```

- Impact: Normal equality can leak tiny timing differences. Exploitation over the network is usually difficult, but webhook secrets are authentication credentials and should be compared with constant-time primitives.
- Fix: Use `secrets.compare_digest()` after normalizing missing headers to empty strings.
- Mitigation: Use long random secrets and rate-limit failed webhook requests.
- False positive notes: This is a hardening issue, not an immediate practical exploit by itself.
- Status: Fixed in `src/mebelbot/telegram_bot.py` and `src/mebelbot/max_bot.py`.

### SBP-006: No app-level Host header validation

- Rule ID: FASTAPI production baseline / TrustedHostMiddleware
- Severity: Low
- Location: `src/mebelbot/app.py`, lines 7 and 43
- Evidence:

```python
from fastapi import FastAPI
app = FastAPI(title="MebelBot", lifespan=lifespan)
```

No `TrustedHostMiddleware` is configured.

- Impact: If deployed directly or behind a permissive proxy, hostile Host headers can affect generated URLs, logs, caches, or future redirects. Current code does not appear to generate URLs from incoming Host, so impact is limited today.
- Fix: Add `TrustedHostMiddleware` with the production hostnames, configurable through environment.
- Mitigation: Enforce Host header validation at the reverse proxy/platform.
- False positive notes: HuggingFace or another platform may already normalize/validate Host, but this is not visible in app code.
- Status: Fixed in `src/mebelbot/app.py`; default trusted hosts are derived from `WEBHOOK_HOST`, or can be overridden by `TRUSTED_HOSTS`.

## Informational / Positive Findings

### INFO-001: No tracked production secrets found

- Location: `.gitignore`, lines 7-10; `.env.example`, lines 1-19; `mvp/main.py`, line 24
- Evidence: `.env` is ignored; `.env.example` contains empty or placeholder values; MVP demo token is read from `TELEGRAM_BOT_TOKEN`.
- Note: The audit intentionally did not print local `.env` values.

### INFO-002: SQL injection risk is low in runtime queries

- Location: `src/mebelbot/storage.py`, lines 128-338
- Evidence: Inserts/selects/updates/deletes use `?` parameters for user-controlled values. `list_failed_submissions()` validates `limit > 0` before binding it.
- Note: `_ensure_column()` uses f-string SQL at lines 121-124, but its current callers pass hardcoded table/column/definition values during schema initialization. Do not expose that helper to user-controlled values.

### INFO-003: Bitrix24 outbound URL comes from configuration, not user input

- Location: `src/mebelbot/bitrix.py`, lines 59-68 and 90-102; `src/mebelbot/config.py`, lines 69-71 and 144-147
- Evidence: Bitrix webhook URL is read from settings and validated as HTTP(S). User chat content is sent as JSON payload, not interpolated into the URL.
- Note: Prefer HTTPS-only for production Bitrix webhooks even though config currently allows HTTP with a validation warning.

## Suggested Fix Order

1. Require Telegram webhook secret in webhook deployments and compare both Telegram/Max secrets with `secrets.compare_digest()`.
2. Disable or protect FastAPI docs/openapi in production.
3. Add webhook request body size limits.
4. Add strict Pydantic models for Max webhook update payloads.
5. Add configurable TrustedHostMiddleware or document edge-level Host validation.
