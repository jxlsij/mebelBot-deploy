# Decisions And Rules

## Architectural Rules

- Keep messenger adapters thin.
- Shared business behavior belongs in `flow.py`, `crm.py`, `domain.py`,
  `content.py`, or `storage.py`.
- Do not collapse Telegram/Max behavior into duplicated adapter logic.
- Do not copy `mvp/main.py` into production code.
- Do not hardcode credentials, tokens, webhook URLs, or Bitrix field IDs.
- Use SQLite persistence even when CRM is unavailable so customer contacts are
  not lost.
- CRM submissions use contact fingerprints to avoid duplicates.
- Source attribution must flow from deep links/QR codes into storage and then
  into Bitrix24.

## Customer Experience Rules

- Demo/customer bot should feel like a furniture bureau bot.
- Use main menu, about, catalog, contacts, guided order form, and confirmation.
- Avoid technical CRM wording in customer-facing copy.
- Keep one-message contact input only as fallback/shortcut; guided form is the
  preferred experience.

## Deployment Rules

- The project is aiogram/FastAPI/ASGI, not a simple `telebot` script.
- HuggingFace deployment should use Docker/ASGI command, not copied `telebot`
  snippets from `deploy guides/`.
- Max production webhooks require HTTPS on port 443 with trusted TLS.
- Telegram can run polling or webhook depending on launch mode.
- After committed changes that should go live, push `main` to both remotes:
  `origin` and `huggingface`.

## Client Handoff Rules

- Customer-facing checklist should hide technical infrastructure details.
- Customer should see ownership/access requirements, not internal endpoints.
- Current implementer/test tokens must be replaced with customer-owned tokens
  before final launch.

## Verification Rules

After code changes:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

After production inputs arrive:

```bash
.venv/bin/mebelbot validate-env
.venv/bin/mebelbot bitrix-validate-fields
.venv/bin/mebelbot bitrix-smoke-test --source smoke_speaker --phone +375291234567 --name "MebelBot Smoke Test"
```

Then generate final QR codes and manually verify every manifest row.
