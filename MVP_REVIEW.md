# MVP Review

The `mvp/` folder contains a colleague's minimal Telegram bot:

- `mvp/main.py` - aiogram polling bot with inline menus and a multi-step order form.
- `mvp/requirements.txt` - minimal dependencies for that demo.

## What It Clarifies

The MVP answers the product question: the customer should see a complete furniture
bureau bot, not only a technical contact collector. The expected demo experience is:

- welcome message with a clear main menu;
- "About" section with company positioning and trust points;
- "Catalog" section with category links and a full-catalog link;
- "Contacts" section with showroom, phone, email, site, and messenger links;
- "Order" flow that asks for name, phone, and request details;
- confirmation step with edit/cancel actions before the request is accepted.

## What Not To Copy

The MVP is not production-ready:

- it contains a hardcoded Telegram bot token;
- it is Telegram-only and does not cover Max;
- it uses in-memory FSM storage;
- it has placeholder catalog/contact URLs;
- it does not persist speaker/source attribution;
- it does not send data to Bitrix24;
- it does not support retries, duplicate protection, or operator tooling.

## Impact On This Project

The current project is architecturally stronger than the MVP: it already has shared
domain logic, Telegram and Max adapters, deep-link source attribution, SQLite
persistence, Bitrix24 submission, retry handling, QR generation, and tests.

The gap is the customer-facing layer. The next iteration should port the MVP's product
shape into the existing architecture:

- keep messenger adapters thin;
- add shared state/flow for guided order collection;
- include the extra "request details" field in CRM comments;
- expose customer-facing copy through centralized content configuration;
- keep Telegram and Max behavior synchronized where platform capabilities allow it.

## Suggested Demo Acceptance Criteria

- `/start` from a speaker QR/deep link saves the source and opens the main menu.
- Telegram and Max both show the same core menu options.
- A customer can open about, catalog, and contacts without typing commands.
- A customer can submit name, phone, and request details through a guided flow.
- Before CRM submission, the customer sees a summary and can confirm, edit, or cancel.
- Bitrix24 receives name, phone, source/speaker, channel/user metadata, and request
  details.
- Failed CRM submissions remain retryable through `mebelbot retry-failed-crm`.
