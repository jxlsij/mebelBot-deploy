# Bitrix24 verification notes

This file records how to verify the Bitrix24 side of MebelBot and how to
interpret the results seen during the 2026-05-27 smoke checks.

## What must be configured

Bitrix24 does not need a custom marketplace app for this project. The bot uses an
incoming webhook and ordinary CRM fields.

Required project settings:

```env
BITRIX24_WEBHOOK_URL=https://...bitrix24.ru/rest/.../...
BITRIX24_ENTITY=lead
BITRIX24_SOURCE_FIELD=UF_CRM_SPEAKER_SRC
```

`BITRIX24_ENTITY` can be `lead` or `deal`. The custom source field must exist on
the same CRM entity:

- if `BITRIX24_ENTITY=lead`, create/check the field on leads;
- if `BITRIX24_ENTITY=deal`, create/check the field on deals.

On HuggingFace Spaces, the required values are set in Variables and Secrets:

- `WEBHOOK_HOST`
- `TELEGRAM_API_BASE`
- `DATABASE_URL`
- `BITRIX24_SOURCE_FIELD`
- `BITRIX24_ENTITY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `BITRIX24_WEBHOOK_URL`

The Bitrix24 webhook itself must remain active and must have CRM permissions.

## Local validation commands

Validate that the configured CRM field codes exist on the selected entity:

```bash
.venv/bin/mebelbot bitrix-validate-fields
```

Known good result from 2026-05-27:

```text
Bitrix24 field validation passed: entity=lead source=UF_CRM_SPEAKER_SRC, phone=PHONE, name=TITLE, comment=COMMENTS
```

Create a disposable CRM item and read it back:

```bash
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

Expected success:

```text
Bitrix24 smoke test passed: entity=lead id=... source_field=UF_CRM_SPEAKER_SRC source=smoke_speaker
```

## How to check the CRM card

Open the created `MebelBot Smoke Test` card in Bitrix24 and check both places:

```text
Комментарий
Канал: telegram
ID пользователя: bitrix-smoke-test
Источник/спикер: smoke_test_source
```

and the separate custom field:

```text
Источник / спикер QR
smoke_test_source
```

If the custom field contains the submitted source code, source attribution works.
This proves that QR/deep-link source values can reach Bitrix24.

## Leads versus deals

The local smoke test follows `BITRIX24_ENTITY`.

If the command prints `entity=lead`, look for the smoke-test item in leads. If
you are viewing deals in Bitrix24, you may be looking at a different deployment
configuration or at records created by another test run.

To make the bot create deals instead of leads, set:

```env
BITRIX24_ENTITY=deal
```

Then make sure `BITRIX24_SOURCE_FIELD` exists on deals and run:

```bash
.venv/bin/mebelbot bitrix-validate-fields
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

## Timeout interpretation

This warning means the bot hit a temporary Bitrix24 transport problem and is
retrying:

```text
WARNING mebelbot.bitrix Temporary Bitrix24 submission failure; retrying
```

This final error means all bounded attempts timed out:

```text
error: Bitrix24 submission failed after 3 attempts: ConnectTimeout:
```

During the 2026-05-27 checks, this happened even though field validation passed.
That means the Bitrix24 webhook and field mapping were valid, but the network/TLS
route to the portal was unstable.

Important: a timeout after sending a create request can still leave a CRM item in
Bitrix24. Before repeating smoke tests, search for `MebelBot Smoke Test` and
delete old disposable records if needed.

## Current verified state

Verified on 2026-05-27:

- Bitrix24 field validation passed for `entity=lead`.
- Source field code: `UF_CRM_SPEAKER_SRC`.
- Smoke-test CRM cards appeared in Bitrix24.
- The CRM card comment contained `Источник/спикер: smoke_test_source`.
- The custom field `Источник / спикер QR` contained `smoke_test_source`.

Conclusion: Bitrix24 platform setup is good enough for source-attribution
testing. Remaining production checks should use real speaker codes from the final
QR manifest and should clean up disposable `MebelBot Smoke Test` records after
verification.
