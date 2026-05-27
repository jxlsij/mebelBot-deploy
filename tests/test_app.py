from fastapi.testclient import TestClient

from mebelbot.app import create_app
from mebelbot.config import Settings


def test_app_health_starts_without_bitrix_configuration(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_disables_openapi_docs_by_default(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get("/openapi.json")

    assert response.status_code == 404


def test_app_limits_webhook_request_body_size(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="max-token",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="secret-value-with-real-length",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
        WEBHOOK_MAX_BODY_BYTES=1024,
    )

    response = TestClient(create_app(settings)).post(
        "/webhooks/max",
        headers={"X-Max-Bot-Api-Secret": "secret-value-with-real-length"},
        content=b'{"update_type":"message_created","text":"' + (b"x" * 2000) + b'"}',
    )

    assert response.status_code == 413
