from __future__ import annotations

from mebelbot.crm import contact_fingerprint
from mebelbot.domain import Channel, ContactData
from mebelbot.storage import SQLiteStorage


def make_contact() -> ContactData:
    return ContactData.create(
        name="Иван",
        phone="+375291234567",
        source_code="speaker_1",
        channel=Channel.max,
        messenger_user_id="777",
    )


def test_sqlite_storage_persists_sources_and_submission_status(tmp_path) -> None:
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'bot.sqlite3'}")
    contact = make_contact()
    fingerprint = contact_fingerprint(contact)

    storage.save_source(Channel.max, "777", "speaker_1")
    storage.upsert_submission(fingerprint, contact)
    storage.mark_submission_failed(fingerprint, "temporary")
    storage.mark_submission_sent(fingerprint, "bitrix-55")

    reopened = SQLiteStorage(f"sqlite:///{tmp_path / 'bot.sqlite3'}")

    assert reopened.get_source(Channel.max, "777") == "speaker_1"
    assert reopened.get_submission(fingerprint) == {
        "fingerprint": fingerprint,
        "status": "sent",
        "bitrix_id": "bitrix-55",
        "last_error": None,
    }


def test_sqlite_storage_keeps_sent_submission_sent_on_upsert(tmp_path) -> None:
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'bot.sqlite3'}")
    contact = make_contact()
    fingerprint = contact_fingerprint(contact)

    storage.upsert_submission(fingerprint, contact)
    storage.mark_submission_sent(fingerprint, "bitrix-55")
    storage.upsert_submission(fingerprint, contact)

    assert storage.get_submission(fingerprint)["status"] == "sent"
    assert storage.get_submission(fingerprint)["bitrix_id"] == "bitrix-55"


def test_sqlite_storage_lists_failed_submissions_for_retry(tmp_path) -> None:
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'bot.sqlite3'}")
    failed = make_contact()
    sent = ContactData.create(
        name="Анна",
        phone="+375291111111",
        source_code="speaker_2",
        channel=Channel.telegram,
        messenger_user_id="888",
    )
    failed_fingerprint = contact_fingerprint(failed)
    sent_fingerprint = contact_fingerprint(sent)

    storage.upsert_submission(failed_fingerprint, failed)
    storage.mark_submission_failed(failed_fingerprint, "temporary")
    storage.upsert_submission(sent_fingerprint, sent)
    storage.mark_submission_sent(sent_fingerprint, "bitrix-56")

    submissions = storage.list_failed_submissions()

    assert len(submissions) == 1
    assert submissions[0].fingerprint == failed_fingerprint
    assert submissions[0].contact.name == "Иван"
    assert submissions[0].contact.channel == Channel.max
    assert submissions[0].last_error == "temporary"
