# MebelBot Project Wiki

This wiki is the durable context layer for the MebelBot project. It summarizes
what exists, why it exists, how to work on it, and what remains blocked.

## Pages

- [[project-overview]] — product goal, current status, and completion boundary.
- [[architecture-map]] — code structure and responsibility boundaries.
- [[runtime-commands]] — local commands, validation, QR generation, and deployment commands.
- [[configuration-and-secrets]] — environment variables, secret handling, and replacement rules.
- [[customer-handoff]] — what the customer must provide and what should stay invisible to them.
- [[bitrix24-context]] — verified CRM behavior, fields, smoke tests, and timeout interpretation.
- [[qr-and-attribution]] — speaker codes, deep links, QR artifacts, and manual verification.
- [[operations-and-monitoring]] — health/readiness, ops status, failed CRM retries, and logs.
- [[decisions-and-rules]] — project conventions and architectural decisions that should not be lost.
- [[session-log-2026-05-27]] — recent work completed and remaining blockers.

## Fast Current State

The Telegram/Max bot implementation, guided customer flow, Bitrix24 integration,
QR generation, persistence, tests, deployment notes, and operator visibility are
implemented. The project is functionally ready for production finalization after
the customer provides final inputs.

Current blockers are external:

- final speaker CSV with stable `code,name` rows;
- real customer Telegram and Max bot usernames/tokens;
- customer Bitrix24 access/settings;
- final production host/launch-mode authority for live webhook registration;
- final acceptance smoke test using real QR links and customer CRM.

Important: any current Telegram/Bitrix24/Max tokens or demo credentials belong to
the current working/testing setup and must be replaced by customer-owned data
before final production launch.
