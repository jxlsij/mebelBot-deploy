# Session Log: 2026-05-27

## Context

The project started with the core implementation already mostly complete and
`TASKS.md` showing production inputs as the main blocker.

## Work Completed

- Read and followed project `AGENTS.md` instructions.
- Confirmed repo was on `main`.
- Ran autopilot-style task completion against `TASKS.md`.
- Added minimal production operations visibility:
  - `/ready`;
  - protected `/ops/status`;
  - `OPS_STATUS_SECRET`;
  - `mebelbot ops-status`;
  - CRM submission status counts.
- Updated tests for readiness/status/secret validation.
- Updated `README.md` production operations section.
- Updated `TASKS.md` to mark locally completed work done and explicitly separate
  production blockers.
- Ran verification:
  - `.venv/bin/pytest -q`: 62 passed;
  - `.venv/bin/ruff check .`: all checks passed;
  - `git diff --check`: clean.
- Committed and pushed:
  - commit `01e5c27` — `Add production ops status checks`;
  - pushed to `origin main`;
  - pushed to `huggingface main`.
- Created customer DOCX checklist:
  - `docs/customer/mebelbot_completion_checklist.docx`.
- Rewrote customer checklist to hide internal technical terms like hosting,
  webhooks, health/readiness endpoints, HTTPS/443, and `.env`.

## Important Observation

Local `mebelbot ops-status` showed 3 failed CRM submissions in the current local
SQLite database. This is useful operational visibility, not necessarily a new
bug. Retry after final CRM configuration:

```bash
.venv/bin/mebelbot retry-failed-crm --limit 10
```

## Remaining Blockers

- Customer final speaker CSV.
- Customer Telegram/Max bot data.
- Customer Bitrix24 settings/access.
- Final launch target/authority to register live endpoints.
- Final production smoke test and QR attribution verification.

## Do Not Forget

Current/demo credentials may belong to the implementer/current working setup.
Before production handoff, replace Telegram, Max, Bitrix24, and deployment
secrets with customer-owned values.
