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
