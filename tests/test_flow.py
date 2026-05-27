from __future__ import annotations

from mebelbot.bitrix import DisabledBitrix24Client
from mebelbot.crm import CRMSubmissionService, contact_fingerprint
from mebelbot.domain import Channel, ContactData
from mebelbot.flow import (
    CRM_SUCCESS,
    CRM_TEMP_ERROR,
    confirm_order_flow,
    handle_contact_text,
    handle_order_text,
    start_order_flow,
)
from mebelbot.storage import SQLiteStorage, Storage


class FakeStorage(Storage):
    def __init__(self) -> None:
        self.sources: dict[tuple[Channel, str], str | None] = {}
        self.submissions: dict[str, dict[str, str | None]] = {}
        self.contacts: list[ContactData] = []
        self.flow_states: dict[tuple[Channel, str], tuple[str, dict[str, str]]] = {}

    def save_source(self, channel: Channel, user_id: str, source_code: str | None) -> None:
        self.sources[(channel, user_id)] = source_code

    def get_source(self, channel: Channel, user_id: str) -> str | None:
        return self.sources.get((channel, user_id))

    def save_contact(self, contact: ContactData, bitrix_id: str | None = None) -> None:
        pass

    def get_submission(self, fingerprint: str) -> dict[str, str | None] | None:
        return self.submissions.get(fingerprint)

    def upsert_submission(self, fingerprint: str, contact: ContactData) -> None:
        self.contacts.append(contact)
        self.submissions[fingerprint] = {
            "fingerprint": fingerprint,
            "status": "pending",
            "bitrix_id": None,
            "last_error": None,
        }

    def mark_submission_sent(self, fingerprint: str, bitrix_id: str) -> None:
        self.submissions[fingerprint] = {
            "fingerprint": fingerprint,
            "status": "sent",
            "bitrix_id": bitrix_id,
            "last_error": None,
        }

    def mark_submission_failed(self, fingerprint: str, error: str) -> None:
        self.submissions[fingerprint] = {
            "fingerprint": fingerprint,
            "status": "failed",
            "bitrix_id": None,
            "last_error": error,
        }

    def save_flow_state(self, channel: Channel, user_id: str, state: str, data: dict[str, str]) -> None:
        self.flow_states[(channel, user_id)] = (state, dict(data))

    def get_flow_state(self, channel: Channel, user_id: str) -> tuple[str, dict[str, str]] | None:
        state = self.flow_states.get((channel, user_id))
        if state is None:
            return None
        return state[0], dict(state[1])

    def clear_flow_state(self, channel: Channel, user_id: str) -> None:
        self.flow_states.pop((channel, user_id), None)


class FakeBitrix:
    def __init__(self) -> None:
        self.contacts: list[ContactData] = []

    async def create_crm_item(self, contact: ContactData) -> str:
        self.contacts.append(contact)
        return "900"


async def test_telegram_contact_flow_uses_saved_source() -> None:
    storage = FakeStorage()
    storage.save_source(Channel.telegram, "42", "speaker_9")
    bitrix = FakeBitrix()

    result = await handle_contact_text(
        text="Иван, +375291234567",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
        crm=CRMSubmissionService(storage, bitrix),
    )

    assert result.reply == CRM_SUCCESS
    assert result.crm_submitted is True
    assert bitrix.contacts[0].source_code == "speaker_9"
    assert bitrix.contacts[0].channel == Channel.telegram


async def test_telegram_contact_flow_rejects_invalid_contact() -> None:
    storage = FakeStorage()
    bitrix = FakeBitrix()

    result = await handle_contact_text(
        text="просто текст",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
        crm=CRMSubmissionService(storage, bitrix),
    )

    assert result.recognized_contact is False
    assert bitrix.contacts == []


async def test_telegram_contact_flow_rejects_short_phone() -> None:
    storage = FakeStorage()
    bitrix = FakeBitrix()

    result = await handle_contact_text(
        text="Иван, 8303820",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
        crm=CRMSubmissionService(storage, bitrix),
    )

    assert result.recognized_contact is False
    assert bitrix.contacts == []


async def test_guided_order_flow_collects_details_and_submits_to_crm() -> None:
    storage = FakeStorage()
    storage.save_source(Channel.telegram, "42", "speaker_9")
    bitrix = FakeBitrix()
    crm = CRMSubmissionService(storage, bitrix)

    start = start_order_flow(
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    name = await handle_order_text(
        text="Иван Петров",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    phone = await handle_order_text(
        text="+375291234567",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    details = await handle_order_text(
        text="Нужна кухня под заказ, светлый фасад",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    submitted = await confirm_order_flow(
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
        crm=crm,
    )

    assert start.show_cancel is True
    assert name.show_cancel is True
    assert phone.show_cancel is True
    assert details.show_confirm is True
    assert submitted.crm_submitted is True
    assert bitrix.contacts[0].name == "Иван Петров"
    assert bitrix.contacts[0].phone == "+375291234567"
    assert bitrix.contacts[0].request_details == "Нужна кухня под заказ, светлый фасад"
    assert bitrix.contacts[0].source_code == "speaker_9"


async def test_guided_order_flow_rejects_short_phone() -> None:
    storage = FakeStorage()
    start_order_flow(
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    await handle_order_text(
        text="Иван Петров",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )

    result = await handle_order_text(
        text="k8303820",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )

    assert result.handled is True
    assert result.show_cancel is True
    assert storage.get_flow_state(Channel.telegram, "42")[0] == "order_phone"


async def test_guided_order_flow_persists_locally_without_bitrix(tmp_path) -> None:
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'demo.sqlite3'}")
    storage.save_source(Channel.telegram, "42", "speaker_9")
    crm = CRMSubmissionService(storage, DisabledBitrix24Client())

    start_order_flow(channel=Channel.telegram, user_id="42", storage=storage)
    await handle_order_text(
        text="Иван Петров",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    await handle_order_text(
        text="+375291234567",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )
    await handle_order_text(
        text="Нужна кухня под заказ, светлый фасад",
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
    )

    result = await confirm_order_flow(
        channel=Channel.telegram,
        user_id="42",
        storage=storage,
        crm=crm,
    )

    contact = ContactData.create(
        name="Иван Петров",
        phone="+375291234567",
        request_details="Нужна кухня под заказ, светлый фасад",
        source_code="speaker_9",
        channel=Channel.telegram,
        messenger_user_id="42",
    )
    submission = storage.get_submission(contact_fingerprint(contact))
    failed = storage.list_failed_submissions()

    assert result.reply == CRM_TEMP_ERROR
    assert result.crm_submitted is False
    assert result.show_main_menu is True
    assert storage.get_flow_state(Channel.telegram, "42") is None
    assert submission is not None
    assert submission["status"] == "failed"
    assert failed[0].contact.name == "Иван Петров"
    assert failed[0].contact.request_details == "Нужна кухня под заказ, светлый фасад"
