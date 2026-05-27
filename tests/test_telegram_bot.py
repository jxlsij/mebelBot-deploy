import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mebelbot.bitrix import DisabledBitrix24Client
from mebelbot.config import Settings
from mebelbot.domain import Channel
from mebelbot.storage import SQLiteStorage
from mebelbot.telegram_bot import (
    build_telegram_router,
    personal_qr_owner_id,
    telegram_qr_source,
)


def test_telegram_qr_source_reuses_existing_deep_link_source(tmp_path) -> None:
    settings = Settings(DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}")
    storage = SQLiteStorage(settings.database_url)
    storage.save_source(Channel.telegram, "42", "speaker_1")

    assert telegram_qr_source(storage, "42") == "speaker_1"
    assert storage.get_source(Channel.telegram, "42") == "speaker_1"


def test_telegram_qr_source_creates_personal_source_when_missing(tmp_path) -> None:
    settings = Settings(DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}")
    storage = SQLiteStorage(settings.database_url)

    assert telegram_qr_source(storage, "42") == "tg_42"
    assert storage.get_source(Channel.telegram, "42") == "tg_42"


def test_personal_qr_owner_id_extracts_owner_for_other_user() -> None:
    assert personal_qr_owner_id("tg_42", "99") == "42"


def test_personal_qr_owner_id_skips_non_personal_and_self_starts() -> None:
    assert personal_qr_owner_id("speaker_1", "99") is None
    assert personal_qr_owner_id("tg_42", "42") is None
    assert personal_qr_owner_id("tg_not_numeric", "99") is None


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
