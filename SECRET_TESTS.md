# Secret-dependent test checklist

Run these checks after real values are added to `.env`.

For Bitrix24-only development, you may use a temporary Bitrix24 cloud trial/demo portal
instead of the client's production CRM. Create an incoming webhook with CRM permissions,
copy the webhook URL into `BITRIX24_WEBHOOK_URL`, set `BITRIX24_ENTITY`, and replace
`BITRIX24_SOURCE_FIELD` with the real `UF_CRM_*` custom field code from that portal.
Detailed Bitrix24 setup notes, leads-vs-deals guidance, and timeout interpretation are
kept in [BITRIX24_CHECKLIST.md](BITRIX24_CHECKLIST.md).

## 1. Validate configuration

```bash
.venv/bin/mebelbot validate-env
```

Expected result:

```text
Environment validation passed.
```

Warnings are acceptable only if you intentionally postpone that item. Any `ERROR`
must be fixed before production checks.

## 2. Verify Bitrix24 field mapping

This creates a disposable CRM item in the real Bitrix24 portal and reads it back.
For a temporary trial/demo portal, the same command verifies only the test portal
mapping; repeat it later against the client's production portal.

```bash
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

Expected result includes:

```text
Bitrix24 smoke test passed
```

The command uses bounded retries for temporary Bitrix24 timeout, transport, and
5xx/429 responses. Repeated failures still indicate a real portal, network, or
field-mapping issue that must be resolved before production use.

Confirm in Bitrix24 that the created lead/deal type matches `BITRIX24_ENTITY` and
that the source field configured in `BITRIX24_SOURCE_FIELD` contains `smoke_speaker`.
If the CLI times out, check Bitrix24 before retrying: the create request may already
have produced a disposable `MebelBot Smoke Test` item.

## 3. Register Max webhook

Run this only after `WEBHOOK_HOST` points to the public HTTPS production host.

```bash
.venv/bin/mebelbot max-subscribe
```

Expected result: Max API returns a successful subscription response for
`bot_started,message_created`.

## 4. Retry queue sanity check

This is safe to run even if there are no failed CRM submissions.

```bash
.venv/bin/mebelbot retry-failed-crm --limit 10
```

Expected result with an empty failed queue:

```text
CRM retry complete: attempted=0 succeeded=0 failed=0
```

## 5. Customer demo smoke test

For production/demo verification, run the bot manually from a real Telegram deep
link and a real Max deep link.

Expected result:

- the bot opens with a customer-friendly main menu;
- the source/speaker from the deep link is saved;
- about, catalog, and contacts sections are reachable by buttons;
- the `Мой QR` button returns a QR image, a Telegram deep link, and a source code;
- opening another user's personal `tg_<id>` QR link sends that owner a Telegram notification;
- the order/contact flow collects name, phone, and request details;
- the confirmation step allows submit, edit, and cancel;
- the submitted CRM item contains the expected source/speaker and request details.

## 6. Regular local checks

These do not require real secrets, but run them after changing `.env` or code.

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```
