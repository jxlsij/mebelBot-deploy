# Customer Handoff

## Customer-Facing Rule

Do not burden the customer with internal hosting/webhook/healthcheck details in
ordinary handoff materials. The customer should see only what they need to
provide or approve:

- speaker list;
- bot accounts/data ownership;
- Bitrix24 access/CRM expectations;
- final texts and links;
- acceptance checks.

## Current Customer Checklist

DOCX file:

```text
docs/customer/mebelbot_completion_checklist.docx
```

This document was rewritten to remove technical infrastructure terms such as
production hosting, webhooks, `/health`, `/ready`, `/ops/status`, HTTPS/443, and
`.env`.

## Customer Must Provide

- Final speaker list as CSV with `code,name`.
- Customer Telegram bot token and public username.
- Customer Max bot token and public username.
- Customer Bitrix24 access/settings for CRM submission.
- Confirmation of whether records should be leads or deals.
- Field in Bitrix24 where source/speaker attribution should be visible.
- Final customer-facing texts and catalog/contact links.

## Customer Should Confirm In Acceptance

- Telegram bot opens from QR.
- Max bot opens from QR.
- Menu, catalog, contacts, and guided order form are understandable.
- A test request appears in Bitrix24.
- The CRM card shows which speaker/QR brought the client.
- Duplicate submissions do not create extra CRM records.
- Final QR codes are ready to distribute to speakers.

## Internal Note

Even though technical launch details are hidden from the customer checklist, they
still exist in `README.md`, [[runtime-commands]], and [[operations-and-monitoring]]
for operators/developers.
