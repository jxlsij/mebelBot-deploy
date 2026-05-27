from __future__ import annotations

import json

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mebelbot.bitrix import DisabledBitrix24Client
from mebelbot.config import Settings
from mebelbot.domain import Channel, ContactData
from mebelbot.max_bot import MaxClient, build_max_router, extract_text, extract_user_id
from mebelbot.storage import SQLiteStorage, Storage


class FakeStorage(Storage):
    def __init__(self) -> None:
        self.sources: dict[tuple[Channel, str], str | None] = {}
        self.contacts: list[ContactData] = []

    def save_source(self, channel: Channel, user_id: str, source_code: str | None) -> None:
        self.sources[(channel, user_id)] = source_code

    def get_source(self, channel: Channel, user_id: str) -> str | None:
        return self.sources.get((channel, user_id))

    def save_contact(self, contact: ContactData, bitrix_id: str | None = None) -> None:
        self.contacts.append(contact)

    def get_submission(self, fingerprint: str) -> dict[str, str | None] | None:
        return None

    def upsert_submission(self, fingerprint: str, contact: ContactData) -> None:
        self.contacts.append(contact)

    def mark_submission_sent(self, fingerprint: str, bitrix_id: str) -> None:
        pass

    def mark_submission_failed(self, fingerprint: str, error: str) -> None:
        pass

    def save_flow_state(self, channel: Channel, user_id: str, state: str, data: dict[str, str]) -> None:
        pass

    def get_flow_state(self, channel: Channel, user_id: str) -> tuple[str, dict[str, str]] | None:
        return None

    def clear_flow_state(self, channel: Channel, user_id: str) -> None:
        pass


class FakeBitrix:
    async def create_crm_item(self, contact: ContactData) -> str:
        return "777"


class FakeMaxClient(MaxClient):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, list[dict[str, Any]] | None]] = []

    async def send_message(
        self,
        user_id: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> None:
        self.sent.append((user_id, text, attachments))

    async def send_text(self, user_id: str, text: str) -> None:
        await self.send_message(user_id, text)


def test_extracts_official_message_created_update() -> None:
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123},
            "body": {"text": "Привет"},
        },
    }

    assert extract_user_id(update) == "123"
    assert extract_text(update) == "Привет"


async def test_max_client_send_text_uses_official_contract() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"message": {"body": {"text": "ok"}}})

    settings = Settings(MAX_BOT_TOKEN="token-123")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await MaxClient(settings, http_client=http_client).send_text("42", "Здравствуйте")

    request = requests[0]
    assert request.url == "https://platform-api.max.ru/messages?user_id=42"
    assert request.headers["Authorization"] == "token-123"
    assert json.loads(request.read()) == {"text": "Здравствуйте"}


def test_max_webhook_handles_bot_started_payload() -> None:
    settings = Settings(
        MAX_BOT_TOKEN="max-token",
        WEBHOOK_SECRET="secret-123",
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
    )
    storage = FakeStorage()
    max_client = FakeMaxClient()
    app = FastAPI()
    app.include_router(build_max_router(settings, storage, FakeBitrix(), max_client))

    response = TestClient(app).post(
        "/webhooks/max",
        headers={"X-Max-Bot-Api-Secret": "secret-123"},
        json={
            "update_type": "bot_started",
            "timestamp": 1573226679188,
            "chat_id": 1234567890,
            "user": {"user_id": 1234567890, "name": "Иван", "username": "ivan_petrov"},
            "payload": "src_speaker_7",
        },
    )

    assert response.status_code == 200
    assert storage.get_source(Channel.max, "1234567890") == "speaker_7"
    assert max_client.sent[0][0] == "1234567890"


def test_max_webhook_rejects_invalid_secret() -> None:
    settings = Settings(
        MAX_BOT_TOKEN="max-token",
        WEBHOOK_SECRET="secret-123",
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
    )
    app = FastAPI()
    app.include_router(build_max_router(settings, FakeStorage(), FakeBitrix(), FakeMaxClient()))

    response = TestClient(app).post(
        "/webhooks/max",
        headers={"X-Max-Bot-Api-Secret": "wrong"},
        json={"update_type": "message_created"},
    )

    assert response.status_code == 401


def test_max_webhook_rejects_unsupported_update_type() -> None:
    settings = Settings(
        MAX_BOT_TOKEN="max-token",
        WEBHOOK_SECRET="secret-123",
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
    )
    app = FastAPI()
    app.include_router(build_max_router(settings, FakeStorage(), FakeBitrix(), FakeMaxClient()))

    response = TestClient(app).post(
        "/webhooks/max",
        headers={"X-Max-Bot-Api-Secret": "secret-123"},
        json={"update_type": "unexpected", "user": {"user_id": 123}},
    )

    assert response.status_code == 400


def test_max_demo_flow_works_without_bitrix_credentials(tmp_path) -> None:
    settings = Settings(
        MAX_BOT_TOKEN="max-token",
        WEBHOOK_SECRET="secret-123",
        BITRIX24_WEBHOOK_URL="",
        CONTENT_LINKS_JSON={"Кухни": "https://example.org/kitchen"},
        DATABASE_URL=f"sqlite:///{tmp_path / 'demo.sqlite3'}",
    )
    storage = SQLiteStorage(settings.database_url)
    max_client = FakeMaxClient()
    app = FastAPI()
    app.include_router(build_max_router(settings, storage, DisabledBitrix24Client(), max_client))
    client = TestClient(app)

    def post_text(text: str):
        return client.post(
            "/webhooks/max",
            headers={"X-Max-Bot-Api-Secret": "secret-123"},
            json={
                "update_type": "message_created",
                "message": {
                    "sender": {"user_id": 123},
                    "body": {"text": text},
                },
            },
        )

    started = client.post(
        "/webhooks/max",
        headers={"X-Max-Bot-Api-Secret": "secret-123"},
        json={
            "update_type": "bot_started",
            "user": {"user_id": 123},
            "payload": "src_speaker_7",
        },
    )
    catalog = post_text("Каталог")
    contacts = post_text("Контакты")
    order = post_text("Оформить заказ")
    name = post_text("Иван Петров")
    phone = post_text("+375291234567")
    details = post_text("Нужна кухня под заказ, светлый фасад")
    confirmed = post_text("Подтвердить")

    failed = storage.list_failed_submissions()

    assert started.status_code == 200
    assert catalog.status_code == 200
    assert contacts.status_code == 200
    assert order.status_code == 200
    assert name.status_code == 200
    assert phone.status_code == 200
    assert details.status_code == 200
    assert confirmed.status_code == 200
    assert confirmed.json() == {"status": "crm_failed"}
    assert storage.get_source(Channel.max, "123") == "speaker_7"
    assert any("https://example.org/kitchen" in text for _, text, _ in max_client.sent)
    assert any("Контакты" in text for _, text, _ in max_client.sent)
    assert failed[0].contact.name == "Иван Петров"
    assert failed[0].contact.request_details == "Нужна кухня под заказ, светлый фасад"
    assert failed[0].contact.source_code == "speaker_7"
