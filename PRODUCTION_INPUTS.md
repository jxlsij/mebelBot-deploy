# Production Inputs Checklist

Use this checklist before generating final speaker QR materials.

## Required From Client

- Final speaker list as CSV with columns `code,name`.
- Public Telegram bot username, without token, for example `mebel_real_bot`.
- Public Max bot username, without token, for example `mebel_real_max_bot`.
- Production HTTPS host for Max webhooks. Max requires HTTPS on port 443 with a trusted TLS certificate.
- Confirmation that Bitrix24 should create `lead` records and store speaker source in `UF_CRM_SPEAKER_SRC`.

## Speaker CSV Rules

- Use `data/speakers.production.template.csv` as the fill-in template.
- `code` must be unique for every speaker.
- `code` may contain only letters, numbers, `_`, and `-`.
- Keep `code` stable after QR files are distributed; changing it breaks source attribution continuity.
- `name` is the human-readable speaker name for the manifest.

## Generation Command

After replacing `data/speakers.csv` with the final client list and setting real usernames:

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --telegram-username TELEGRAM_USERNAME --max-username MAX_USERNAME --out data/qr
```

Or, when `TELEGRAM_BOT_USERNAME` and `MAX_BOT_USERNAME` are configured in `.env`:

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --out data/qr
```

## Manual Verification

For each row in `data/qr/manifest.csv`:

1. Open the Telegram link and the Max link.
2. Confirm the bot opens with the expected source code in the deep link.
3. Submit a test request through the guided form.
4. Confirm Bitrix24 receives `UF_CRM_SPEAKER_SRC` equal to that row's `code`.
5. Archive or delete the test CRM item after verification.
