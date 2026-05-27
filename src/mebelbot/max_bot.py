from __future__ import annotations

from secrets import compare_digest
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from mebelbot.bitrix import Bitrix24Client
from mebelbot.config import Settings

import logging

logger = logging.getLogger(__name__)

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
from mebelbot.qr import max_link, qr_png_bytes, validate_bot_username
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


def max_main_menu(content) -> list[dict[str, Any]]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {"type": "message", "text": content.about_button},
                        {"type": "message", "text": content.catalog_button},
                    ],
                    [
                        {"type": "message", "text": content.order_button},
                        {"type": "message", "text": content.contacts_button},
                    ],
                    [{"type": "message", "text": content.qr_button}],
                ]
            },
        }
    ]


def max_cancel_menu(content) -> list[dict[str, Any]]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [[{"type": "message", "text": content.cancel_button, "intent": "negative"}]]
            },
        }
    ]


def max_confirm_menu(content) -> list[dict[str, Any]]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {"type": "message", "text": content.confirm_button, "intent": "positive"},
                        {"type": "message", "text": content.edit_button},
                    ],
                    [{"type": "message", "text": content.cancel_button, "intent": "negative"}],
                ]
            },
        }
    ]


def max_markup_for_result(result, content) -> list[dict[str, Any]] | None:
    if result.show_confirm:
        return max_confirm_menu(content)
    if result.show_cancel:
        return max_cancel_menu(content)
    if result.show_main_menu:
        return max_main_menu(content)
    return None


def max_reply_for_result(result, content) -> str:
    if result.show_confirm:
        return result.reply
    if result.show_cancel:
        return result.reply
    return result.reply


class MaxClient:
    def __init__(self, token: str, http_client: httpx.AsyncClient | None = None) -> None:
        self.token = token
        self.base_url = "https://platform-api.max.ru"
        self._client = http_client

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": self.token}

    async def send_message(
        self,
        user_id: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"text": text}
        if attachments:
            payload["attachments"] = attachments
        await self._post(
            "/messages",
            params={"user_id": user_id},
            json=payload,
        )

    async def send_image(
        self,
        user_id: str,
        text: str,
        image_bytes: bytes,
        filename: str = "qr.png",
    ) -> None:
        token = None
        try:
            # Step 1: Get upload URL
            upload_resp = await self._post("/uploads", params={"type": "image"})
            upload_data = upload_resp.json()
            if "url" not in upload_data:
                logger.error("Max API upload URL request failed", extra={"response": upload_data})
                raise RuntimeError(f"Max API did not return upload URL: {upload_data}")
            upload_url = upload_data["url"]

            # Step 2: Upload file (Try 'file' then 'data')
            async def try_upload(field_name: str) -> str | None:
                files = {field_name: (filename, image_bytes, "image/png")}
                try:
                    if self._client is not None:
                        resp = await self._client.post(upload_url, files=files)
                    else:
                        async with httpx.AsyncClient(timeout=30) as client:
                            resp = await client.post(upload_url, files=files)
                    
                    resp.raise_for_status()
                    result = resp.json()
                    return result.get("token")
                except Exception as e:
                    logger.debug(f"Upload attempt with field '{field_name}' failed: {e}")
                    return None

            token = await try_upload("file")
            if not token:
                token = await try_upload("data")

            if not token:
                logger.error("Max API file upload failed to return token with both 'file' and 'data'")
                raise RuntimeError("Max API did not return file token")

            # Step 3: Send message with image attachment
            attachments = [
                {
                    "type": "image",
                    "payload": {"token": token},
                }
            ]
            await self.send_message(user_id, text, attachments=attachments)

        except Exception:
            logger.exception("Failed to send image to Max, falling back to text-only")
            # Fallback to plain text so the user at least gets the link
            await self.send_message(user_id, text)

    async def send_text(self, user_id: str, text: str) -> None:
        await self.send_message(user_id, text)

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


def max_qr_source(storage: Storage, user_id: str) -> str:
    existing_source = storage.get_source(Channel.max, user_id)
    if existing_source:
        return existing_source
    source = f"mx_{user_id}"
    storage.save_source(Channel.max, user_id, source)
    return source


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
    reply_markup = max_main_menu(content)

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
            await max_client.send_message(user_id, content.welcome_text, attachments=reply_markup)
            return {"status": "ok"}

        if text.startswith("/start"):
            source = parse_start_payload(text)
            if source:
                storage.save_source(Channel.max, user_id, source)
            storage.clear_flow_state(Channel.max, user_id)
            await max_client.send_message(user_id, content.welcome_text, attachments=reply_markup)
            return {"status": "ok"}

        if command_matches(text, content.main_menu_button):
            storage.clear_flow_state(Channel.max, user_id)
            await max_client.send_message(user_id, content.welcome_text, attachments=reply_markup)
            return {"status": "ok"}

        if command_matches(text, content.about_button):
            await max_client.send_message(user_id, content.about_text, attachments=reply_markup)
            return {"status": "ok"}

        if command_matches(text, content.catalog_button) or command_matches(text, content.links_button):
            await max_client.send_message(user_id, links_text(settings, content), attachments=reply_markup)
            return {"status": "ok"}

        if command_matches(text, content.contacts_button):
            await max_client.send_message(user_id, content.contacts_text, attachments=reply_markup)
            return {"status": "ok"}

        if command_matches(text, content.qr_button):
            try:
                username = (
                    validate_bot_username(settings.max_bot_username, field_name="MAX_BOT_USERNAME")
                    if settings.max_bot_username
                    else None
                )
            except ValueError:
                username = None

            if not username:
                await max_client.send_message(user_id, content.qr_unavailable_text, attachments=reply_markup)
                return {"status": "ok"}

            source = max_qr_source(storage, user_id)
            link = max_link(username, source)
            await max_client.send_image(
                user_id,
                f"{content.qr_caption_text}\n\nСсылка: {link}\nИсточник: {source}",
                qr_png_bytes(link),
                filename=f"{source}-max.png",
            )
            return {"status": "ok"}

        if command_matches(text, content.order_button) or command_matches(text, content.contact_button):
            result = start_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_message(
                user_id, result.reply, attachments=max_markup_for_result(result, content)
            )
            return {"status": "ok"}

        if command_matches(text, content.cancel_button):
            result = cancel_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_message(
                user_id, result.reply, attachments=max_markup_for_result(result, content)
            )
            return {"status": "ok"}

        if command_matches(text, content.edit_button):
            result = edit_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                content=content,
            )
            await max_client.send_message(
                user_id, result.reply, attachments=max_markup_for_result(result, content)
            )
            return {"status": "ok"}

        if command_matches(text, content.confirm_button):
            result = await confirm_order_flow(
                channel=Channel.max,
                user_id=user_id,
                storage=storage,
                crm=crm,
                content=content,
            )
            await max_client.send_message(
                user_id, result.reply, attachments=max_markup_for_result(result, content)
            )
            return {"status": "ok" if result.crm_submitted else "crm_failed"}

        order_result = await handle_order_text(
            text=text,
            channel=Channel.max,
            user_id=user_id,
            storage=storage,
            content=content,
        )
        if order_result.handled:
            await max_client.send_message(
                user_id,
                order_result.reply,
                attachments=max_markup_for_result(order_result, content),
            )
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
            await max_client.send_message(user_id, unknown_command_reply(content), attachments=reply_markup)
            return {"status": "ok"}

        if not result.crm_submitted:
            await max_client.send_message(user_id, result.reply, attachments=reply_markup)
            return {"status": "crm_failed"}

        await max_client.send_message(user_id, result.reply, attachments=reply_markup)
        return {"status": "ok"}

    return router
