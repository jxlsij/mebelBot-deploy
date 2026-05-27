# Project Overview

## Purpose

MebelBot is a Python chatbot project for Telegram and Max. It provides a shared
customer-facing flow for a furniture bureau, tracks lead source attribution
through deep links and QR codes, and submits collected contacts/orders to
Bitrix24 CRM.

## Product Shape

The customer-facing experience should feel like a real furniture bureau bot, not
a technical CRM test. The visible flow includes:

- welcome/main menu;
- "About" / company information;
- catalog/category links;
- contacts;
- guided order/contact form;
- confirmation step before submission;
- success and temporary CRM-error messages.

The colleague MVP in `mvp/main.py` is a UX/content reference only. It must not be
used as production code because it is Telegram-only, in-memory, and uses
placeholder data.

## Current Status

Implemented:

- Telegram adapter with aiogram.
- Max webhook adapter with FastAPI.
- Shared domain/source parsing.
- Shared order/contact flow.
- SQLite persistence for source attribution, flow state, contacts, and CRM
  submission state.
- Bitrix24 webhook client with bounded retries.
- Duplicate submission protection via contact fingerprint.
- Failed CRM submission retry command.
- QR/deep-link generator for Telegram and Max.
- Ad-hoc Telegram personal QR generation with owner notification.
- Centralized bot content with `BOT_CONTENT_JSON` overrides.
- Docker/ASGI deployment notes.
- Health/readiness/ops visibility.
- Regression tests for domain, flow, QR, storage, Telegram, Max, Bitrix24, config,
  and app endpoints.

## Completion Boundary

The code side is essentially complete. Remaining work requires customer-owned
production inputs and live external systems:

- final speaker list;
- customer Telegram/Max bot data;
- customer Bitrix24 connection and selected CRM entity/field mapping;
- production launch target and authority to register live messenger endpoints;
- final smoke test and acceptance check.

## Customer-Facing Handoff

The current customer-facing DOCX checklist is:

`docs/customer/mebelbot_completion_checklist.docx`

That document intentionally hides technical infrastructure details. It asks the
customer only for business-facing inputs and access ownership.
