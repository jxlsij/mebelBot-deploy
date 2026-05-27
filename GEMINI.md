# MebelBot Project Instructions

MebelBot is a Python-based multichannel chatbot system (Telegram and Max) designed for a furniture bureau. It features deep-link/QR-based speaker attribution and integration with Bitrix24 CRM for lead/deal creation.

## Project Overview

- **Main Technologies:** Python 3.11+, `aiogram` (Telegram), `FastAPI` (Max webhooks/API), `SQLite` (Persistence), `httpx` (CRM Client), `pydantic` (Data Validation).
- **Core Features:**
  - Parallel bot experience on Telegram and Max.
  - Guided order/contact collection flow with confirmation steps.
  - Source attribution through unique deep links and QR codes.
  - Bitrix24 CRM integration with field mapping and retry logic.
  - Operational monitoring and CLI tools for management.
- **Architecture:** Follows a clean separation between messenger adapters (`telegram_bot.py`, `max_bot.py`) and shared business logic (`flow.py`, `domain.py`, `crm.py`).

## Key Directories and Files

- `src/mebelbot/`: Main source code.
  - `app.py`: FastAPI application, webhooks, and health endpoints.
  - `telegram_bot.py`: Telegram adapter (aiogram).
  - `max_bot.py`: Max adapter and API client.
  - `flow.py`: Shared state machine for the guided order flow.
  - `crm.py` & `bitrix.py`: CRM submission and Bitrix24 client logic.
  - `storage.py`: SQLite persistence layer.
  - `qr.py`: QR code and deep-link generation logic.
  - `__main__.py`: CLI entrypoint.
- `data/`: CSV templates for speakers and generated QR artifacts.
- `omx_wiki/`: Detailed internal documentation and architecture maps.
- `tests/`: Comprehensive test suite covering all modules.

## Building and Running

### Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### Key Commands
- **Run Telegram (Polling):** `mebelbot telegram`
- **Run Webhook Server:** `uvicorn mebelbot.app:app --reload`
- **Run Tests:** `pytest`
- **Linting:** `ruff check .`
- **Environment Validation:** `mebelbot validate-env`
- **Bitrix24 Smoke Test:** `mebelbot bitrix-smoke-test`
- **Generate QR Codes:** `mebelbot-qr --speakers data/speakers.csv --out data/qr`
- **Retry Failed CRM:** `mebelbot retry-failed-crm`
- **Check Ops Status:** `mebelbot ops-status`

## Development Conventions

- **Separation of Concerns:** Keep messenger adapters thin. Shared business logic, flow state transitions, and CRM rules must reside in core modules (`flow.py`, `crm.py`, etc.).
- **Type Safety:** Use type hints throughout the codebase. Pydantic models are used for configuration and data validation.
- **Persistence:** All stateful data (user sources, contacts, flow state) must be persisted in SQLite to ensure resilience across restarts.
- **Configuration:** Use `.env` for all secrets and portal-specific settings. Validate configuration using `mebelbot validate-env`.
- **Bot Content:** Customer-facing copy is centralized in `content.py` and can be overridden via `BOT_CONTENT_JSON`.
- **Testing:** New features or bug fixes must include corresponding tests in the `tests/` directory.

## Deployment

The project is configured for deployment on **HuggingFace Spaces** using the provided `Dockerfile`.
- Port: `7860` (default for Spaces).
- Environment variables for webhooks (`WEBHOOK_HOST`, `TELEGRAM_WEBHOOK_SECRET`, etc.) must be set in the Space settings.
- Max production webhooks require HTTPS on port 443; HuggingFace provides the necessary TLS termination.
