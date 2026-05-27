# Configuration And Secrets

## Rule

Never hardcode credentials. Use `.env` locally and deployment variables/secrets
in production.

## Important Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_API_BASE`
- `TELEGRAM_WEBHOOK_SECRET`
- `MAX_BOT_TOKEN`
- `MAX_BOT_USERNAME`
- `BITRIX24_WEBHOOK_URL`
- `DATABASE_URL`
- `WEBHOOK_HOST`
- `WEBHOOK_SECRET`
- `OPS_STATUS_SECRET`
- `BITRIX24_ENTITY`
- `BITRIX24_SOURCE_FIELD`
- `BITRIX24_PHONE_FIELD`
- `BITRIX24_NAME_FIELD`
- `BITRIX24_COMMENT_FIELD`
- `CONTENT_LINKS_JSON`
- `BOT_CONTENT_JSON`

## Customer Token Replacement

Current working/test credentials may belong to the implementer/current setup.
Before final production launch, customer-owned credentials must replace temporary
or implementer-owned data for:

- Telegram bot token and username;
- Max bot token and username;
- Bitrix24 webhook URL and CRM settings;
- production webhook/admin secrets;
- any deployment-specific secrets.

The customer-facing checklist says this without exposing infrastructure detail:
temporary implementer data must be fully replaced and must not be used in final
operation.

## Validation

Run:

```bash
.venv/bin/mebelbot validate-env
```

The validator checks for missing values, placeholder defaults, invalid URLs,
unsupported database URLs, malformed content links, short secrets, and default
Bitrix source-field placeholders. It does not print secret values.

## Content Overrides

`BOT_CONTENT_JSON` can override customer-facing copy without code changes. It
maps to fields in `BotContent`, including menu labels, welcome/about/catalog/
contacts text, order prompts, confirmation/edit/cancel text, validation messages,
CRM success text, and temporary CRM error text.

`CONTENT_LINKS_JSON` configures catalog/category links. Values must be HTTP/HTTPS
URLs.

## SQLite

The runtime currently supports only `sqlite:///...` database URLs. Default:

```text
sqlite:///data/mebelbot.sqlite3
```
