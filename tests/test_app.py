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


def test_app_ready_checks_database(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ops_status_requires_explicit_secret(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get("/ops/status")

    assert response.status_code == 404


def test_ops_status_reports_integration_and_submission_counts(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="1234567890:abcdefghijklmnopqrstuvwxyz",
        TELEGRAM_WEBHOOK_SECRET="telegram-secret-value",
        MAX_BOT_TOKEN="max-token-value-with-real-length",
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/secret/",
        WEBHOOK_SECRET="secret-value-with-real-length",
        OPS_STATUS_SECRET="operator-secret-value",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get(
        "/ops/status",
        headers={"X-MebelBot-Admin-Secret": "operator-secret-value"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["telegram_webhook_enabled"] is True
    assert body["max_webhook_enabled"] is True
    assert body["bitrix24_configured"] is True
    assert body["crm_submissions"] == {"pending": 0, "sent": 0, "failed": 0}


def test_ops_status_rejects_wrong_secret(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        MAX_BOT_TOKEN="",
        BITRIX24_WEBHOOK_URL="",
        WEBHOOK_SECRET="",
        OPS_STATUS_SECRET="operator-secret-value",
        DATABASE_URL=f"sqlite:///{tmp_path / 'mebelbot.sqlite3'}",
    )

    response = TestClient(create_app(settings)).get(
        "/ops/status",
        headers={"X-MebelBot-Admin-Secret": "wrong-secret"},
    )

    assert response.status_code == 401
