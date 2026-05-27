import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mebelbot.bitrix import DisabledBitrix24Client
from mebelbot.config import Settings
from mebelbot.storage import SQLiteStorage
from mebelbot.telegram_bot import build_telegram_router


def test_telegram_webhook_rejects_missing_secret_header(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="1234567890:abcdefghijklmnopqrstuvwxyz",
        TELEGRAM_WEBHOOK_SECRET="telegram-secret-value",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )
    storage = SQLiteStorage(settings.database_url)
    app = FastAPI()
    router, bot = build_telegram_router(settings, storage, DisabledBitrix24Client())
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post("/webhooks/telegram", json={})
    try:
        asyncio.run(bot.session.close())
    except RuntimeError:
        pass

    assert response.status_code == 401
