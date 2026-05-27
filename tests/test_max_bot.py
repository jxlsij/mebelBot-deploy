from __future__ import annotations

import json

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mebelbot.config import Settings
from mebelbot.domain import Channel, ContactData
from mebelbot.max_bot import MaxClient, build_max_router, extract_text, extract_user_id
from mebelbot.storage import Storage


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
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, user_id: str, text: str) -> None:
        self.sent.append((user_id, text))


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

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await MaxClient("token-123", http_client=http_client).send_text("42", "Здравствуйте")

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
