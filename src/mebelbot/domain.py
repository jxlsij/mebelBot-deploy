from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class Channel(StrEnum):
    telegram = "telegram"
    max = "max"


@dataclass(frozen=True)
class SpeakerSource:
    code: str
    name: str

    def __post_init__(self) -> None:
        if not SOURCE_RE.fullmatch(self.code):
            raise ValueError("Speaker source code must contain only letters, numbers, '_' or '-'")


@dataclass(frozen=True)
class ContactData:
    name: str
    phone: str
    source_code: str | None
    channel: Channel
    messenger_user_id: str
    created_at: datetime
    request_details: str | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone: str,
        source_code: str | None,
        channel: Channel,
        messenger_user_id: str,
        request_details: str | None = None,
    ) -> "ContactData":
        return cls(
            name=name.strip(),
            phone=phone.strip(),
            source_code=source_code,
            channel=channel,
            messenger_user_id=str(messenger_user_id),
            created_at=datetime.now(tz=UTC),
            request_details=request_details.strip() if request_details else None,
        )


def parse_start_payload(text: str | None) -> str | None:
    if not text:
        return None
    parts = text.strip().split(maxsplit=1)
    payload = parts[1] if len(parts) == 2 and parts[0] == "/start" else parts[0]
    payload = payload.removeprefix("src_")
    return payload if SOURCE_RE.fullmatch(payload) else None
