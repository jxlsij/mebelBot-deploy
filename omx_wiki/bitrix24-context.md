# Bitrix24 Context

## Integration Shape

The project uses an incoming Bitrix24 webhook with CRM permissions. It can create
either leads or deals depending on `BITRIX24_ENTITY`.

Source attribution is stored in the configured custom field:

```text
BITRIX24_SOURCE_FIELD=UF_CRM_SPEAKER_SRC
```

Current verified/tested entity: `lead`.

## Required Settings

```env
BITRIX24_WEBHOOK_URL=https://...bitrix24.ru/rest/.../...
BITRIX24_ENTITY=lead
BITRIX24_SOURCE_FIELD=UF_CRM_SPEAKER_SRC
BITRIX24_PHONE_FIELD=PHONE
BITRIX24_NAME_FIELD=TITLE
BITRIX24_COMMENT_FIELD=COMMENTS
```

If switching to `deal`, the source field must exist on deals, not only on leads.

## Validation Commands

```bash
.venv/bin/mebelbot bitrix-validate-fields
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

Known good validation from 2026-05-27:

```text
Bitrix24 field validation passed: entity=lead source=UF_CRM_SPEAKER_SRC, phone=PHONE, name=TITLE, comment=COMMENTS
```

## Verified Behavior

On 2026-05-27, a forced-healthy-IP check validated lead fields, created test lead
`id=16`, read it back, and confirmed:

```text
UF_CRM_SPEAKER_SRC=smoke_test_source
```

The CRM card comment also included:

```text
Канал: telegram
ID пользователя: bitrix-smoke-test
Источник/спикер: smoke_test_source
```

## Timeout Notes

Bitrix24 DNS/TLS routing for `b24-ymgd84.bitrix24.ru` showed a mixed pool where
some IPs completed TLS quickly and others timed out. The code now retries
Bitrix24 POST requests with bounded exponential backoff.

A `ConnectTimeout` does not automatically prove credentials or field mapping are
wrong. It may be a transient transport issue. A timeout after a create request
can still leave a CRM item in Bitrix24, so search for and delete old disposable
`MebelBot Smoke Test` records before repeating tests.

## Remaining Production Check

Repeat validation and smoke tests against the customer's real Bitrix24 portal and
with real speaker codes from the final QR manifest.
