from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mebelbot.bitrix import Bitrix24Client, DisabledBitrix24Client
from mebelbot.config import Settings, get_settings
from mebelbot.max_bot import build_max_router
from mebelbot.storage import SQLiteStorage
from mebelbot.telegram_bot import build_telegram_router, configure_telegram_webhook


def create_app(settings: Settings | None = None) -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = settings or get_settings()
    storage = SQLiteStorage(settings.database_url)
    try:
        bitrix = Bitrix24Client(settings)
    except RuntimeError:
        logging.warning("Bitrix24 is not configured; webhook app will run without CRM submission")
        bitrix = DisabledBitrix24Client()

    telegram_bot = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        if telegram_bot is not None:
            await configure_telegram_webhook(settings, telegram_bot)
        try:
            yield
        finally:
            if telegram_bot is not None:
                await telegram_bot.session.close()

    app = FastAPI(title="MebelBot", lifespan=lifespan)

    if settings.telegram_bot_token:
        telegram_router, telegram_bot = build_telegram_router(settings, storage, bitrix)
        app.include_router(telegram_router)

    if settings.max_bot_token and settings.webhook_secret:
        app.include_router(build_max_router(settings, storage, bitrix))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
