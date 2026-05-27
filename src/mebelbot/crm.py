from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from mebelbot.bitrix import Bitrix24NotConfiguredError
from mebelbot.domain import ContactData
from mebelbot.storage import Storage

logger = logging.getLogger(__name__)


def contact_fingerprint(contact: ContactData) -> str:
    normalized_phone = re.sub(r"\D+", "", contact.phone)
    source = contact.source_code or ""
    raw = "|".join(
        [
            contact.channel.value,
            contact.messenger_user_id,
            normalized_phone,
            source,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetryFailedSubmissionsResult:
    attempted: int
    succeeded: int
    failed: int


class BitrixClient(Protocol):
    async def create_crm_item(self, contact: ContactData, *, attempts: int = 3) -> str: ...


class CRMSubmissionService:
    def __init__(self, storage: Storage, bitrix: BitrixClient) -> None:
        self.storage = storage
        self.bitrix = bitrix

    async def submit_contact(self, contact: ContactData) -> str:
        fingerprint = contact_fingerprint(contact)
        existing = self.storage.get_submission(fingerprint)
        if existing and existing.get("status") == "sent" and existing.get("bitrix_id"):
            logger.info(
                "Skipping duplicate CRM submission",
                extra={
                    "fingerprint": fingerprint,
                    "bitrix_id": existing["bitrix_id"],
                    "channel": contact.channel.value,
                },
            )
            return str(existing["bitrix_id"])

        self.storage.upsert_submission(fingerprint, contact)
        logger.info(
            "Submitting contact to Bitrix24",
            extra={"fingerprint": fingerprint, "channel": contact.channel.value},
        )
        try:
            bitrix_id = await self.bitrix.create_crm_item(contact)
        except Bitrix24NotConfiguredError as error:
            self.storage.mark_submission_failed(fingerprint, str(error))
            logger.warning(
                "Bitrix24 submission skipped because CRM is not configured",
                extra={"fingerprint": fingerprint, "channel": contact.channel.value},
            )
            raise
        except Exception as error:
            self.storage.mark_submission_failed(fingerprint, str(error))
            logger.exception(
                "Bitrix24 submission failed",
                extra={"fingerprint": fingerprint, "channel": contact.channel.value},
            )
            raise

        self.storage.mark_submission_sent(fingerprint, bitrix_id)
        logger.info(
            "Bitrix24 submission succeeded",
            extra={
                "fingerprint": fingerprint,
                "bitrix_id": bitrix_id,
                "channel": contact.channel.value,
            },
        )
        return bitrix_id

    async def retry_failed_submissions(self, *, limit: int | None = None) -> RetryFailedSubmissionsResult:
        submissions = self.storage.list_failed_submissions(limit=limit)
        succeeded = 0
        failed = 0

        for submission in submissions:
            contact = submission.contact
            logger.info(
                "Retrying failed Bitrix24 submission",
                extra={"fingerprint": submission.fingerprint, "channel": contact.channel.value},
            )
            try:
                bitrix_id = await self.bitrix.create_crm_item(contact)
            except Exception as error:
                failed += 1
                self.storage.mark_submission_failed(submission.fingerprint, str(error))
                logger.exception(
                    "Bitrix24 submission retry failed",
                    extra={"fingerprint": submission.fingerprint, "channel": contact.channel.value},
                )
                continue

            succeeded += 1
            self.storage.mark_submission_sent(submission.fingerprint, bitrix_id)
            logger.info(
                "Bitrix24 submission retry succeeded",
                extra={
                    "fingerprint": submission.fingerprint,
                    "bitrix_id": bitrix_id,
                    "channel": contact.channel.value,
                },
            )

        return RetryFailedSubmissionsResult(
            attempted=len(submissions),
            succeeded=succeeded,
            failed=failed,
        )
