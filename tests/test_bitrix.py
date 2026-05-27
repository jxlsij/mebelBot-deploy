import httpx
import pytest

import mebelbot.bitrix
from mebelbot.__main__ import _run_bitrix_field_validation
from mebelbot.bitrix import Bitrix24Client
from mebelbot.config import Settings
from mebelbot.domain import Channel, ContactData


def test_bitrix_payload_contains_source_field() -> None:
    settings = Settings(
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
        BITRIX24_SOURCE_FIELD="UF_CRM_123",
    )
    contact = ContactData.create(
        name="Иван",
        phone="+375291234567",
        source_code="speaker_1",
        channel=Channel.telegram,
        messenger_user_id="42",
    )

    payload = Bitrix24Client(settings).build_payload(contact)

    assert payload["fields"]["UF_CRM_123"] == "speaker_1"
    assert payload["fields"]["PHONE"][0]["VALUE"] == "+375291234567"


async def test_bitrix_retries_temporary_http_errors(monkeypatch) -> None:
    settings = Settings(BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/")
    contact = ContactData.create(
        name="Иван",
        phone="+375291234567",
        source_code="speaker_1",
        channel=Channel.telegram,
        messenger_user_id="42",
    )
    responses = [
        httpx.Response(503, json={"error": "temporary"}),
        httpx.Response(200, json={"result": 123}),
    ]
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responses.pop(0)

    async def no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(mebelbot.bitrix.asyncio, "sleep", no_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await Bitrix24Client(settings, http_client=http_client).create_crm_item(contact)

    assert result == "123"
    assert len(requests) == 2


async def test_bitrix_get_crm_item_uses_configured_entity_method() -> None:
    settings = Settings(
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
        BITRIX24_ENTITY="deal",
    )
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": {"ID": "456", "UF_CRM_123": "speaker_1"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await Bitrix24Client(settings, http_client=http_client).get_crm_item("456")

    assert result["result"]["ID"] == "456"
    assert str(requests[0].url).endswith("/crm.deal.get.json")
    assert requests[0].content == b'{"id":"456"}'


async def test_bitrix_get_crm_fields_uses_configured_entity_method() -> None:
    settings = Settings(
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
        BITRIX24_ENTITY="lead",
    )
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": {"TITLE": {"title": "Name"}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await Bitrix24Client(settings, http_client=http_client).get_crm_fields()

    assert result == {"TITLE": {"title": "Name"}}
    assert str(requests[0].url).endswith("/crm.lead.fields.json")
    assert requests[0].content == b"{}"


class FakeBitrixFields:
    def __init__(self, fields: dict[str, object]) -> None:
        self.fields = fields

    async def get_crm_fields(self) -> dict[str, object]:
        return self.fields


async def test_bitrix_field_validation_reports_missing_mapping() -> None:
    settings = Settings(
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
        BITRIX24_SOURCE_FIELD="UF_CRM_123",
    )
    bitrix = FakeBitrixFields({"TITLE": {}, "PHONE": {}, "COMMENTS": {}})

    with pytest.raises(RuntimeError, match="missing=UF_CRM_123"):
        await _run_bitrix_field_validation(bitrix, settings)  # type: ignore[arg-type]


async def test_bitrix_field_validation_accepts_configured_mapping() -> None:
    settings = Settings(
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/token/",
        BITRIX24_SOURCE_FIELD="UF_CRM_123",
    )
    bitrix = FakeBitrixFields({"TITLE": {}, "PHONE": {}, "COMMENTS": {}, "UF_CRM_123": {}})

    result = await _run_bitrix_field_validation(bitrix, settings)  # type: ignore[arg-type]

    assert "Bitrix24 field validation passed" in result
    assert "source=UF_CRM_123" in result
