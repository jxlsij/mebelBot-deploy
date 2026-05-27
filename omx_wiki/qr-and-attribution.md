# QR And Attribution

## Purpose

Each speaker receives unique Telegram and Max deep links encoded as QR PNG files.
When a user opens a bot through a link, the source code is stored and later sent
to Bitrix24.

## Speaker CSV

Final production input should be:

```csv
code,name
ivanov,Иван Иванов
petrova,Анна Петрова
```

Rules:

- `code` must be unique.
- `code` may contain only letters, numbers, `_`, and `-`.
- `code` should remain stable after QR files are distributed.
- `name` is the human-readable speaker name for manifests.

Template:

```text
data/speakers.production.template.csv
```

Demo data:

```text
data/speakers.csv
data/qr-demo/
```

## Generation

```bash
.venv/bin/mebelbot-qr --speakers data/speakers.csv --telegram-username TELEGRAM_USERNAME --max-username MAX_USERNAME --out data/qr
```

The generator rejects placeholder usernames and invalid source codes before
writing production artifacts.

## Output

Expected output:

- Telegram QR PNG per speaker.
- Max QR PNG per speaker.
- `data/qr/manifest.csv` with source code, speaker name, links, and PNG paths.

## Manual Verification

For every final manifest row:

1. Open the Telegram link.
2. Open the Max link.
3. Submit a test request through the guided form.
4. Confirm Bitrix24 receives the same speaker/source code in the configured
   source field.
5. Archive/delete disposable test CRM records after verification.

## Personal Telegram QR

Telegram has a `Мой QR` menu button. It sends a PNG QR and deep link.

Behavior:

- if the user already has a deep-link source, reuse it;
- otherwise create `tg_<telegram_user_id>`;
- if another Telegram user opens a personal `tg_<owner_id>` QR, notify the owner
  with starter display name, Telegram ID, and source code;
- self-starts and shared speaker codes do not notify owners.
