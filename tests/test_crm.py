from __future__ import annotations

from mebelbot.crm import CRMSubmissionService, contact_fingerprint
from mebelbot.domain import Channel, ContactData
from mebelbot.storage import Storage, StoredContactSubmission


class FakeStorage(Storage):
    def __init__(self) -> None:
        self.submissions: dict[str, dict[str, str | None]] = {}
        self.upserts = 0

    def save_source(self, channel: Channel, user_id: str, source_code: str | None) -> None:
        pass

    def get_source(self, channel: Channel, user_id: str) -> str | None:
        return None

    def save_contact(self, contact: ContactData, bitrix_id: str | None = None) -> None:
        pass

    def get_submission(self, fingerprint: str) -> dict[str, str | None] | None:
        return self.submissions.get(fingerprint)

    def list_failed_submissions(self, limit: int | None = None) -> list[StoredContactSubmission]:
        failed = []
        for fingerprint, submission in self.submissions.items():
            if submission["status"] == "failed":
                failed.append(
                    StoredContactSubmission(
                        fingerprint=fingerprint,
                        contact=make_contact(),
                        status="failed",
                        bitrix_id=None,
                        last_error=submission["last_error"],
                    )
                )
        return failed[:limit]

    def upsert_submission(self, fingerprint: str, contact: ContactData) -> None:
        self.upserts += 1
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


class FakeBitrix:
    def __init__(self) -> None:
        self.calls = 0

    async def create_crm_item(self, contact: ContactData) -> str:
        self.calls += 1
        return "321"


def make_contact(phone: str = "+375 (29) 123-45-67") -> ContactData:
    return ContactData.create(
        name="Иван",
        phone=phone,
        source_code="speaker_1",
        channel=Channel.telegram,
        messenger_user_id="42",
    )


def test_contact_fingerprint_normalizes_phone_format() -> None:
    assert contact_fingerprint(make_contact("+375291234567")) == contact_fingerprint(
        make_contact("+375 (29) 123-45-67")
    )


async def test_crm_submission_skips_already_sent_contact() -> None:
    contact = make_contact()
    fingerprint = contact_fingerprint(contact)
    storage = FakeStorage()
    storage.submissions[fingerprint] = {
        "fingerprint": fingerprint,
        "status": "sent",
        "bitrix_id": "already-created",
        "last_error": None,
    }
    bitrix = FakeBitrix()

    result = await CRMSubmissionService(storage, bitrix).submit_contact(contact)

    assert result == "already-created"
    assert bitrix.calls == 0


async def test_crm_retry_failed_submissions_marks_successful_retry_sent() -> None:
    contact = make_contact()
    fingerprint = contact_fingerprint(contact)
    storage = FakeStorage()
    storage.submissions[fingerprint] = {
        "fingerprint": fingerprint,
        "status": "failed",
        "bitrix_id": None,
        "last_error": "temporary",
    }
    bitrix = FakeBitrix()

    result = await CRMSubmissionService(storage, bitrix).retry_failed_submissions()

    assert result.attempted == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert bitrix.calls == 1
    assert storage.submissions[fingerprint]["status"] == "sent"
    assert storage.submissions[fingerprint]["bitrix_id"] == "321"
