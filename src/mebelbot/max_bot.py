from __future__ import annotations

from secrets import compare_digest
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from mebelbot.bitrix import Bitrix24Client
from mebelbot.config import Settings
from mebelbot.content import bot_content, command_matches, links_text, unknown_command_reply
from mebelbot.crm import CRMSubmissionService
from mebelbot.domain import Channel, parse_start_payload
from mebelbot.flow import (
    cancel_order_flow,
    confirm_order_flow,
    edit_order_flow,
    handle_contact_text,
    handle_order_text,
    start_order_flow,
)
from mebelbot.storage import Storage


class MaxUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str | int | None = None
    id: str | int | None = None

    def user_id_text(self) -> str | None:
        value = self.user_id if self.user_id is not None else self.id
        return str(value) if value is not None else None


class MaxMessageBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class MaxMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: MaxUser | None = None
    user: MaxUser | None = None
    body: MaxMessageBody | None = None
    text: str | None = None
    user_id: str | int | None = None

    def text_value(self) -> str:
        if self.text:
            return self.text
        if self.body and self.body.text:
            return self.body.text
        return ""

    def user_id_text(self) -> str | None:
        user = self.sender or self.user
        if user:
            return user.user_id_text()
        return str(self.user_id) if self.user_id is not None else None


class MaxWebhookUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_type: str
    message: MaxMessage | None = None
    user: MaxUser | None = None
    payload: str | None = None
    text: str | None = None
    user_id: str | int | None = None

    def text_value(self) -> str:
        if self.message:
            return self.message.text_value()
        return self.text or ""

    def user_id_text(self) -> str | None:
        if self.message:
            user_id = self.message.user_id_text()
            if user_id:
                return user_id
        if self.user:
            user_id = self.user.user_id_text()
            if user_id:
                return user_id
        return str(self.user_id) if self.user_id is not None else None


def extract_text(update: dict[str, Any]) -> str:
    message = update.get("message") if isinstance(update.get("message"), dict) else update
    body = message.get("body") if isinstance(message.get("body"), dict) else {}
    return str(message.get("text") or body.get("text") or "")


def extract_user_id(update: dict[str, Any]) -> str | None:
    message = update.get("message") if isinstance(update.get("message"), dict) else update
    user = message.get("sender") or message.get("user") or update.get("user")
    if isinstance(user, dict):
        value = user.get("user_id") or user.get("id")
        return str(value) if value is not None else None
    value = message.get("user_id") or update.get("user_id")
    return str(value) if value is not None else None


def max_menu_text(content) -> str:
    return (
        f"{content.welcome_text}\n\n"
        "Меню:\n"
        f"- {content.about_button}\n"
        f"- {content.catalog_button}\n"
        f"- {content.order_button}\n"
        f"- {content.contacts_button}"
    )


def append_action_hint(text: str, content, *, confirm: bool = False, cancel: bool = False) -> str:
    if confirm:
        return (
            f"{text}\n\n"
            f"Ответьте: {content.confirm_button}, {content.edit_button} или {content.cancel_button}."
        )
    if cancel:
        return f"{text}\n\nЧтобы прервать заявку, отправьте: {content.cancel_button}."
    return f"{text}\n\nЧтобы вернуться в меню, отправьте: {content.main_menu_button}."


def max_reply_for_result(result, content) -> str:
    if result.show_confirm:
        return append_action_hint(result.reply, content, confirm=True)
    if result.show_cancel:
        return append_action_hint(result.reply, content, cancel=True)
    if result.show_main_menu:
        return f"{result.reply}\n\n{max_menu_text(content)}"
    return result.reply


class MaxClient:
    def __init__(self, token: str, http_client: httpx.AsyncClient | None = None) -> None:
        self.token = token
        self.base_url = "https://platform-api.max.ru"
        self._client = http_client

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": self.token}

    async def send_text(self, user_id: str, text: str) -> None:
        await self._post(
            "/messages",
            params={"user_id": user_id},
            json={"text": text},
        )

    async def subscribe_webhook(self, webhook_url: str, secret: str) -> dict[str, Any]:
        response = await self._post(
            "/subscriptions",
            json={
                "url": webhook_url,
                "update_types": ["bot_started", "message_created"],
                "secret": secret,
            },
        )
        return response.json()

    async def _post(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if self._client is not None:
            response = await self._client.post(
                f"{self.base_url}{path}",
                params=params,
                headers=self.headers,
                json=json,
            )
            response.raise_for_status()
            return response

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                params=params,
                headers=self.headers,
                json=json,
            )
            response.raise_for_status()
            return response


def build_max_router(
    settings: Settings,
    storage: Storage,
    bitrix: Bitrix24Client,
    max_client: MaxClient | None = None,
) -> APIRouter:
    settings.require_max()
    router = APIRouter()
    max_client = max_client or MaxClient(settings.max_bot_token)
    crm = CRMSubmissionService(storage, bitrix)
    content = bot_content(settings)

    @router.post("/webhooks/max")
    async def max_webhook(
        request: Request,
        x_max_bot_api_secret: str | None = Header(default=None),
    ) -> dict[str, str]:
        if not compare_digest(x_max_bot_api_secret or "", settings.webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid Max webhook secret")

        try:
            update = MaxWebhookUpdate.model_validate(await request.json())
        except ValidationError as error:
            raise HTTPException(status_code=400, detail="Invalid Max webhook payload") from error

        if update.update_type not in {"bot_started", "message_created"}:
            raise HTTPException(status_code=400, detail="Unsupported Max update type")

        text = update.text_value()
        user_id = update.user_id_text()
        if not user_id:
            return {"status": "ignored"}

        if update.update_type == "bot_started":
            source = parse_start_payload(update.payload or "")
            if source:
                storage.save_source(Channel.max, user_id, source)
            storage.clear_flow_state(Channel.max, user_id)
            await max_client.send_text(user_id, max_menu_text(content))
            return {"status": "ok"}

        if text.startswith("/start"):
            source = parse_start_payload(text)
            if source:
                storage.save_source(Channel.max, user_id, source)
            storage.clear_flow_state(Channel.max, user_id)
            await max_client.send_text(user_id, max_menu_text(content))
            return {"status": "ok"}

        if command_matches(text, content.main_menu_button):
            storage.clear_flow_state(Channel.max, user_id)
            await max_client.send_text(user_id, max_menu_text(content))
            return {"status": "ok"}

        if command_matches(text, content.about_button):
            await max_client.send_text(user_id, append_action_hint(content.about_text, content))
            return {"status": "ok"}

        if command_matches(text, content.catalog_button) or command_matches(text, content.links_button):
            await max_client.send_text(user_id, append_action_hint(links_text(settings, content), content))
            return {"status": "ok"}

        if command_matches(text, content.contacts_button):
            await max_client.send_text(user_id, append_action_hint(content.contacts_text, content))
            return {"status": "ok"}

        if command_matches(text, content.order_button) or command_matches(text, content.contact_button):
            result = start_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_text(user_id, max_reply_for_result(result, content))
            return {"status": "ok"}

        if command_matches(text, content.cancel_button):
            result = cancel_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_text(user_id, max_reply_for_result(result, content))
            return {"status": "ok"}

        if command_matches(text, content.edit_button):
            result = edit_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_text(user_id, max_reply_for_result(result, content))
            return {"status": "ok"}

        if command_matches(text, content.confirm_button):
            result = await confirm_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                crm=crm,
                content=content,
            )
            await max_client.send_text(user_id, max_reply_for_result(result, content))
            return {"status": "ok" if result.crm_submitted else "crm_failed"}

        order_result = await handle_order_text(
            text=text,
            channel=Channel.max,
            user_id=user_id,
            storage=storage,
            content=content,
        )
        if order_result.handled:
            await max_client.send_text(user_id, max_reply_for_result(order_result, content))
            return {"status": "ok"}

        result = await handle_contact_text(
            text=text,
            channel=Channel.max,
            user_id=user_id,
            storage=storage,
            crm=crm,
            content=content,
        )
        if not result.recognized_contact:
            await max_client.send_text(user_id, unknown_command_reply(content))
            return {"status": "ok"}

        if not result.crm_submitted:
            await max_client.send_text(user_id, result.reply)
            return {"status": "crm_failed"}

        await max_client.send_text(user_id, result.reply)
        return {"status": "ok"}

    return router
