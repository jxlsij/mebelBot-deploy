## 🎯 Current
- [ ] Collect production inputs from the client before generating final QR materials.
  - Needed: real speaker list with unique `code,name` rows, real Telegram bot username, real Max bot username, and production host details for Max HTTPS webhooks.
- [ ] Replace `data/speakers.csv` demo rows with the real speaker list, regenerate QR codes with real Telegram/Max bot usernames, and manually verify that every deep link stores the correct source code.
  - Blocked until the real speaker list and bot usernames are provided. The QR generator now rejects placeholder usernames and invalid source codes before writing production artifacts.

## 📋 Backlog
- [ ] Verify Bitrix24 integration against the real portal once credentials are available: confirm whether the project should create leads or deals, confirm field mappings, and prove the speaker/source field receives the expected value.
  - Needed: `BITRIX24_WEBHOOK_URL`, `BITRIX24_ENTITY`, `BITRIX24_SOURCE_FIELD`, and any custom name/phone/comment field codes. Run `mebelbot bitrix-validate-fields` before the smoke test.
- [ ] Optionally run the Bitrix24 smoke test against a temporary Bitrix24 trial/demo portal before client CRM access is ready.
  - This can verify webhook creation, lead/deal payloads, and custom source field mapping, but production validation must be repeated on the client's real Bitrix24 portal.
- [ ] Keep the simple one-message contact input available only if needed as an operator shortcut or fallback; the customer demo should prefer the guided form.
- [ ] Adapt the free HuggingFace + Cloudflare Worker deployment guide for this aiogram/FastAPI project, including Dockerfile, ASGI command, Telegram API proxy support, and Max webhook limitations.
- [ ] Add production deployment notes for running Telegram polling and Max webhooks under a process manager, including HTTPS/443 requirements for Max.
- [ ] Register production webhooks/subscriptions on the live host: Max via `mebelbot max-subscribe` and Telegram webhook setup if Telegram is moved from polling to webhook mode.
- [ ] Add minimal production monitoring and operator visibility for failed CRM submissions, Telegram/Max API errors, Bitrix24 errors, logs, and `/health`.
- [ ] Run the final production smoke test: Telegram deep link to Bitrix24, Max deep link to Bitrix24, duplicate submission protection, and QR-to-source attribution.

## ✅ Done
- [x] Initialize the bot project structure with dependency management, runtime entrypoint, configuration loading, and development scripts
- [x] Define shared domain models and storage for speaker sources, users, contact data, and lead creation state so Telegram and Max can use the same logic
- [x] Implement Telegram bot onboarding with deep-link source parsing, base menu, content sections, useful links, and contact data collection
- [x] Implement Max bot adapter with matching onboarding, content, useful links, source tracking, and contact data collection
- [x] Build the Bitrix24 integration client using webhooks, including configurable field mapping for contacts, lead/deal creation, and speaker source transfer
- [x] Add QR/deep-link generation for an arbitrary list of speakers and document how to produce links and QR codes for each source
- [x] Add environment validation and basic tests around source attribution and Bitrix24 payload creation
- [x] Write setup and operator documentation covering env vars, local run commands, speaker configuration, QR generation, and deployment notes
- [x] Validate Max API request/response contract against the production bot documentation and adjust the adapter endpoints/payloads if needed
- [x] Add Max webhook subscription command and documentation for production webhook registration
- [x] Add retry-safe CRM submission handling and richer operational logging
- [x] Expand tests around Max webhook parsing and Bitrix24 retry behavior
- [x] Expand tests around Telegram contact flow, SQLite persistence, and QR generation
- [x] Add an operator command to retry failed CRM submissions from SQLite.
- [x] Add a Bitrix24 smoke-test command that creates a test CRM item and verifies the configured speaker/source field.
- [x] Centralize bot content and allow production text overrides through BOT_CONTENT_JSON.
- [x] Review colleague MVP in `mvp/` and capture it as the demo UX reference.
- [x] Map the MVP Telegram-only UX to the shared Telegram/Max architecture without copying secrets or collapsing the shared business logic into adapter code.
- [x] Extend centralized bot content so production/demo copy can cover welcome text, about text, catalog text/buttons, contacts text, order prompts, confirmation, edit, cancel, and success/error messages.
- [x] Send the guided order request details to Bitrix24 through the configured comment field.
- [x] Bring the customer-facing bot demo to the shape shown in `mvp/main.py`: main menu, "About", "Catalog", "Contacts", and a multi-step order/contact form with confirmation.
- [x] Finalize customer-ready bot content: welcome text, about/company text, catalog/category links, contacts, button labels, successful submission text, invalid input text, and temporary CRM error text.
- [x] Prepare a demo speaker source list and QR generation manifest so production QR links can be checked before distribution.
- [x] Remove the hardcoded Telegram token from `mvp/main.py`; demo tokens are read from environment only.
- [x] Clean up the interrupted Bitrix24 trial smoke-test work before the next deploy.
  - Kept useful fixes: `httpx` INFO logs no longer expose webhook URLs, CLI errors are concise, and local `.env` Bitrix values stay out of Git.
  - Removed the experimental long sync fallback; `bitrix-smoke-test` uses one CRM creation attempt.
  - On 2026-05-27, `.venv/bin/mebelbot bitrix-validate-fields` passed for `lead` with source field `UF_CRM_SPEAKER_SRC`; one bounded `bitrix-smoke-test` failed with `ConnectTimeout`, so the trial portal is not stable enough for repeat testing.
- [x] Keep the bot demo-ready while Bitrix24 access is unavailable.
  - Added regression coverage proving Telegram/shared guided order collection persists failed CRM submissions in SQLite when Bitrix24 is disabled.
  - Added regression coverage proving Max menu, catalog links, contacts, guided order collection, source attribution, and SQLite persistence continue to work without CRM credentials.

## ⚠️ Rules
- Bot must run in parallel for Telegram and Max with synchronized information and links.
- After every committed project change, push `main` to both GitHub (`origin`) and the
  HuggingFace Space remote (`huggingface`) so source control and deployment stay in sync.
- Each speaker must have a unique deep link that can be encoded as a QR code and saved as the client source.
- Collect client contact data through the bot interface and persist it even while CRM is unavailable.
- Bitrix24 lead/deal creation is deferred until portal access is available; when enabled, pass speaker/source information into a dedicated CRM field.
- Keep shared business logic independent from messenger-specific adapters.
- Credentials and Bitrix24 field IDs must be configured through environment variables or config files, not hardcoded.
- Treat `mvp/` as a product/UX reference only. Do not copy its placeholder URLs, in-memory-only state, or Telegram-only architecture into production code.
- The customer demo should feel like a real furniture bureau bot, not a technical CRM test: menu sections and guided order flow matter as much as the CRM submission.

## 📎 Source
Brief: spec.md
MVP reference: `mvp/main.py`
