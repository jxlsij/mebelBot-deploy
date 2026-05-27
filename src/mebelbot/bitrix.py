from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from mebelbot.config import Settings
from mebelbot.domain import ContactData

logger = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = 3


class Bitrix24Error(RuntimeError):
    pass


class Bitrix24TransientError(Bitrix24Error):
    pass


class Bitrix24NotConfiguredError(Bitrix24Error):
    pass


class DisabledBitrix24Client:
    async def create_crm_item(self, contact: ContactData, *, attempts: int = 3) -> str:
        raise Bitrix24NotConfiguredError("Bitrix24 is not configured")

    async def get_crm_item(self, item_id: str) -> dict[str, Any]:
        raise Bitrix24NotConfiguredError("Bitrix24 is not configured")


class Bitrix24Client:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        settings.require_bitrix()
        self.settings = settings
        self._client = http_client

    def build_payload(self, contact: ContactData) -> dict[str, Any]:
        comment_lines = [
            f"Канал: {contact.channel.value}",
            f"ID пользователя: {contact.messenger_user_id}",
            f"Источник/спикер: {contact.source_code or 'unknown'}",
        ]
        if contact.request_details:
            comment_lines.extend(["", "Пожелание клиента:", contact.request_details])

        fields: dict[str, Any] = {
            self.settings.bitrix24_name_field: contact.name,
            self.settings.bitrix24_phone_field: [{"VALUE": contact.phone, "VALUE_TYPE": "WORK"}],
            self.settings.bitrix24_comment_field: "\n".join(comment_lines),
        }
        if contact.source_code:
            fields[self.settings.bitrix24_source_field] = contact.source_code
        return {"fields": fields}

    async def create_crm_item(self, contact: ContactData, *, attempts: int = DEFAULT_ATTEMPTS) -> str:
        method = "crm.lead.add.json" if self.settings.bitrix24_entity == "lead" else "crm.deal.add.json"
        webhook = str(self.settings.bitrix24_webhook_url).rstrip("/")
        payload = self.build_payload(contact)
        return await self._post_crm_item(
            f"{webhook}/{method}",
            payload,
            attempts=attempts,
            operation="submission",
            log_extra={"channel": contact.channel.value},
        )

    async def get_crm_item(self, item_id: str) -> dict[str, Any]:
        method = "crm.lead.get.json" if self.settings.bitrix24_entity == "lead" else "crm.deal.get.json"
        webhook = str(self.settings.bitrix24_webhook_url).rstrip("/")
        return await self._post_crm_json(
            f"{webhook}/{method}",
            {"id": item_id},
            operation="readback",
        )

    async def get_crm_fields(self) -> dict[str, Any]:
        method = (
            "crm.lead.fields.json"
            if self.settings.bitrix24_entity == "lead"
            else "crm.deal.fields.json"
        )
        webhook = str(self.settings.bitrix24_webhook_url).rstrip("/")
        data = await self._post_crm_json(f"{webhook}/{method}", {}, operation="field validation")
        fields = data.get("result")
        if not isinstance(fields, dict):
            raise Bitrix24Error("Bitrix24 fields response did not contain a field map")
        return fields

    async def _post_crm_item(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        attempts: int = DEFAULT_ATTEMPTS,
        operation: str = "request",
        log_extra: dict[str, Any] | None = None,
    ) -> str:
        data = await self._post_crm_json(
            url,
            payload,
            attempts=attempts,
            operation=operation,
            log_extra=log_extra,
        )
        return str(data.get("result", ""))

    async def _post_crm_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        attempts: int = DEFAULT_ATTEMPTS,
        operation: str = "request",
        log_extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await self._send_post(url, payload)
            except (httpx.TimeoutException, httpx.TransportError, Bitrix24TransientError) as error:
                last_error = error
                if attempt >= attempts:
                    break
                delay = 0.5 * (2 ** (attempt - 1))
                logger.warning(
                    "Temporary Bitrix24 %s failure; retrying",
                    operation,
                    extra={
                        "attempt": attempt,
                        "delay": delay,
                        "error_type": type(error).__name__,
                        **(log_extra or {}),
                    },
                )
                await asyncio.sleep(delay)

        if last_error is None:
            detail = "unknown error"
        else:
            detail = f"{type(last_error).__name__}: {last_error}"
        raise Bitrix24Error(f"Bitrix24 {operation} failed after {attempts} attempts: {detail}")

    async def _send_post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is not None:
            response = await self._client.post(url, json=payload)
            return self._parse_crm_response(response)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
        return self._parse_crm_response(response)

    def _parse_crm_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in {429, 500, 502, 503, 504}:
            raise Bitrix24TransientError(f"Bitrix24 temporary HTTP {response.status_code}")
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            message = f"Bitrix24 error: {data['error']}: {data.get('error_description', '')}"
            if data["error"] in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                raise Bitrix24TransientError(message)
            raise Bitrix24Error(message)
        return data
