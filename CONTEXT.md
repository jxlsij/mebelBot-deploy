# MebelBot Context Entry Point

Start here when returning to the project after a break.

## Canonical Context

The durable project context is stored in:

```text
omx_wiki/
```

Read first:

1. `omx_wiki/index.md`
2. `omx_wiki/project-overview.md`
3. `omx_wiki/customer-handoff.md`
4. `omx_wiki/session-log-2026-05-27.md`
5. `TASKS.md`

## Current One-Screen Summary

MebelBot is a Telegram + Max furniture-bureau chatbot with shared guided order
flow, QR/deep-link speaker attribution, SQLite persistence, and Bitrix24 CRM
submission.

The code side is largely complete. Remaining work is blocked on customer-owned
production data and access:

- final speaker CSV;
- customer Telegram and Max bot data;
- customer Bitrix24 settings/access;
- final launch authority;
- final QR and CRM smoke-test acceptance.

Important: current/demo Telegram, Max, Bitrix24, or deployment credentials may
belong to the implementer/current setup. They must be replaced with
customer-owned credentials before final production launch.

## Latest Verification

After the last code change:

```text
.venv/bin/pytest -q      -> 62 passed
.venv/bin/ruff check .   -> all checks passed
```

Latest deployed commit:

```text
01e5c27 Add production ops status checks
```
