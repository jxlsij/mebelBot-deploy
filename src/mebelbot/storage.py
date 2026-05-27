from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from mebelbot.domain import Channel, ContactData

SubmissionStatus = Literal["pending", "sent", "failed"]


@dataclass(frozen=True)
class StoredContactSubmission:
    fingerprint: str
    contact: ContactData
    status: SubmissionStatus
    bitrix_id: str | None
    last_error: str | None


class Storage:
    def save_source(self, channel: Channel, user_id: str, source_code: str | None) -> None:
        raise NotImplementedError

    def get_source(self, channel: Channel, user_id: str) -> str | None:
        raise NotImplementedError

    def save_contact(self, contact: ContactData, bitrix_id: str | None = None) -> None:
        raise NotImplementedError

    def get_submission(self, fingerprint: str) -> dict[str, str | None] | None:
        raise NotImplementedError

    def list_failed_submissions(self, limit: int | None = None) -> list[StoredContactSubmission]:
        raise NotImplementedError

    def submission_status_counts(self) -> dict[SubmissionStatus, int]:
        raise NotImplementedError

    def upsert_submission(self, fingerprint: str, contact: ContactData) -> None:
        raise NotImplementedError

    def mark_submission_sent(self, fingerprint: str, bitrix_id: str) -> None:
        raise NotImplementedError

    def mark_submission_failed(self, fingerprint: str, error: str) -> None:
        raise NotImplementedError

    def save_flow_state(self, channel: Channel, user_id: str, state: str, data: dict[str, str]) -> None:
        raise NotImplementedError

    def get_flow_state(self, channel: Channel, user_id: str) -> tuple[str, dict[str, str]] | None:
        raise NotImplementedError

    def clear_flow_state(self, channel: Channel, user_id: str) -> None:
        raise NotImplementedError


class SQLiteStorage(Storage):
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// DATABASE_URL is supported in the initial runtime")
        self.path = Path(database_url.removeprefix("sqlite:///"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_sources (
                    channel TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    source_code TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel, user_id)
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT UNIQUE,
                    channel TEXT NOT NULL,
                    messenger_user_id TEXT NOT NULL,
                    source_code TEXT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    request_details TEXT,
                    bitrix_id TEXT,
                    status TEXT NOT NULL DEFAULT 'sent',
                    last_error TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS flow_states (
                    channel TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel, user_id)
                );
                """
            )
            self._ensure_column(db, "contacts", "fingerprint", "TEXT")
            self._ensure_column(db, "contacts", "status", "TEXT NOT NULL DEFAULT 'sent'")
            self._ensure_column(db, "contacts", "last_error", "TEXT")
            self._ensure_column(db, "contacts", "request_details", "TEXT")
            db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_fingerprint
                ON contacts(fingerprint)
                WHERE fingerprint IS NOT NULL
                """
            )

    def _ensure_column(self, db: sqlite3.Connection, table: str, name: str, definition: str) -> None:
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if name not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def save_source(self, channel: Channel, user_id: str, source_code: str | None) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO user_sources (channel, user_id, source_code)
                VALUES (?, ?, ?)
                ON CONFLICT(channel, user_id)
                DO UPDATE SET source_code = excluded.source_code, updated_at = CURRENT_TIMESTAMP
                """,
                (channel.value, str(user_id), source_code),
            )

    def get_source(self, channel: Channel, user_id: str) -> str | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT source_code FROM user_sources WHERE channel = ? AND user_id = ?",
                (channel.value, str(user_id)),
            ).fetchone()
        return str(row["source_code"]) if row and row["source_code"] else None

    def save_contact(self, contact: ContactData, bitrix_id: str | None = None) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO contacts (
                    channel,
                    messenger_user_id,
                    source_code,
                    name,
                    phone,
                    request_details,
                    bitrix_id,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', ?)
                """,
                (
                    contact.channel.value,
                    contact.messenger_user_id,
                    contact.source_code,
                    contact.name,
                    contact.phone,
                    contact.request_details,
                    bitrix_id,
                    contact.created_at.isoformat(),
                ),
            )

    def get_submission(self, fingerprint: str) -> dict[str, str | None] | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT fingerprint, status, bitrix_id, last_error
                FROM contacts
                WHERE fingerprint = ?
                """,
                (fingerprint,),
            ).fetchone()
        return dict(row) if row else None

    def list_failed_submissions(self, limit: int | None = None) -> list[StoredContactSubmission]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")

        query = """
            SELECT
                fingerprint,
                channel,
                messenger_user_id,
                source_code,
                name,
                phone,
                request_details,
                bitrix_id,
                status,
                last_error,
                created_at
            FROM contacts
            WHERE status = 'failed' AND fingerprint IS NOT NULL
            ORDER BY created_at ASC, id ASC
        """
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self._connect() as db:
            rows = db.execute(query, params).fetchall()

        submissions: list[StoredContactSubmission] = []
        for row in rows:
            contact = ContactData(
                name=str(row["name"]),
                phone=str(row["phone"]),
                request_details=str(row["request_details"]) if row["request_details"] else None,
                source_code=str(row["source_code"]) if row["source_code"] else None,
                channel=Channel(str(row["channel"])),
                messenger_user_id=str(row["messenger_user_id"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            submissions.append(
                StoredContactSubmission(
                    fingerprint=str(row["fingerprint"]),
                    contact=contact,
                    status="failed",
                    bitrix_id=str(row["bitrix_id"]) if row["bitrix_id"] else None,
                    last_error=str(row["last_error"]) if row["last_error"] else None,
                )
            )
        return submissions

    def submission_status_counts(self) -> dict[SubmissionStatus, int]:
        counts: dict[SubmissionStatus, int] = {"pending": 0, "sent": 0, "failed": 0}
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM contacts
                GROUP BY status
                """
            ).fetchall()

        for row in rows:
            status = str(row["status"])
            if status in counts:
                counts[status] = int(row["count"])
        return counts

    def upsert_submission(self, fingerprint: str, contact: ContactData) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO contacts (
                    fingerprint,
                    channel,
                    messenger_user_id,
                    source_code,
                    name,
                    phone,
                    request_details,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                ON CONFLICT(fingerprint)
                DO UPDATE SET
                    name = excluded.name,
                    phone = excluded.phone,
                    request_details = excluded.request_details,
                    source_code = excluded.source_code,
                    status = CASE
                        WHEN contacts.status = 'sent' THEN contacts.status
                        ELSE 'pending'
                    END,
                    last_error = CASE
                        WHEN contacts.status = 'sent' THEN contacts.last_error
                        ELSE NULL
                    END
                """,
                (
                    fingerprint,
                    contact.channel.value,
                    contact.messenger_user_id,
                    contact.source_code,
                    contact.name,
                    contact.phone,
                    contact.request_details,
                    contact.created_at.isoformat(),
                ),
            )

    def mark_submission_sent(self, fingerprint: str, bitrix_id: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE contacts
                SET status = 'sent', bitrix_id = ?, last_error = NULL
                WHERE fingerprint = ?
                """,
                (bitrix_id, fingerprint),
            )

    def mark_submission_failed(self, fingerprint: str, error: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE contacts
                SET status = 'failed', last_error = ?
                WHERE fingerprint = ?
                """,
                (error[:1000], fingerprint),
            )

    def save_flow_state(self, channel: Channel, user_id: str, state: str, data: dict[str, str]) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO flow_states (channel, user_id, state, data_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel, user_id)
                DO UPDATE SET
                    state = excluded.state,
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (channel.value, str(user_id), state, json.dumps(data, ensure_ascii=False)),
            )

    def get_flow_state(self, channel: Channel, user_id: str) -> tuple[str, dict[str, str]] | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT state, data_json
                FROM flow_states
                WHERE channel = ? AND user_id = ?
                """,
                (channel.value, str(user_id)),
            ).fetchone()
        if not row:
            return None
        parsed = json.loads(str(row["data_json"]))
        data = {str(key): str(value) for key, value in parsed.items()} if isinstance(parsed, dict) else {}
        return str(row["state"]), data

    def clear_flow_state(self, channel: Channel, user_id: str) -> None:
        with self._connect() as db:
            db.execute(
                "DELETE FROM flow_states WHERE channel = ? AND user_id = ?",
                (channel.value, str(user_id)),
            )
