from __future__ import annotations

import logging
from dataclasses import dataclass

from mebelbot.bitrix import Bitrix24NotConfiguredError
from mebelbot.content import (
    DEFAULT_CONTENT,
    BotContent,
    invalid_contact_reply,
    order_summary,
    parse_name_phone,
)
from mebelbot.crm import CRMSubmissionService
from mebelbot.domain import Channel, ContactData
from mebelbot.storage import Storage

logger = logging.getLogger(__name__)

CONTACT_PARSE_ERROR = invalid_contact_reply()
CRM_TEMP_ERROR = DEFAULT_CONTENT.crm_temp_error_text
CRM_SUCCESS = DEFAULT_CONTENT.crm_success_text
ORDER_STATE_NAME = "order_name"
ORDER_STATE_PHONE = "order_phone"
ORDER_STATE_DETAILS = "order_details"
ORDER_STATE_CONFIRM = "order_confirm"


@dataclass(frozen=True)
class ContactFlowResult:
    reply: str
    recognized_contact: bool
    crm_submitted: bool


@dataclass(frozen=True)
class OrderFlowResult:
    reply: str
    handled: bool
    crm_submitted: bool = False
    show_main_menu: bool = False
    show_cancel: bool = False
    show_confirm: bool = False


async def handle_contact_text(
    *,
    text: str,
    channel: Channel,
    user_id: str,
    storage: Storage,
    crm: CRMSubmissionService,
    content: BotContent = DEFAULT_CONTENT,
) -> ContactFlowResult:
    parsed = parse_name_phone(text)
    if not parsed:
        return ContactFlowResult(
            reply=invalid_contact_reply(content),
            recognized_contact=False,
            crm_submitted=False,
        )

    name, phone = parsed
    source = storage.get_source(channel, user_id)
    contact = ContactData.create(
        name=name,
        phone=phone,
        source_code=source,
        channel=channel,
        messenger_user_id=user_id,
    )
    try:
        await crm.submit_contact(contact)
    except Bitrix24NotConfiguredError:
        logger.warning("CRM is not configured; contact was saved locally")
        return ContactFlowResult(
            reply=content.crm_temp_error_text,
            recognized_contact=True,
            crm_submitted=False,
        )
    except Exception:
        logger.exception("Failed to submit contact to CRM", extra={"channel": channel.value})
        return ContactFlowResult(
            reply=content.crm_temp_error_text,
            recognized_contact=True,
            crm_submitted=False,
        )

    return ContactFlowResult(
        reply=content.crm_success_text,
        recognized_contact=True,
        crm_submitted=True,
    )


def start_order_flow(
    *,
    channel: Channel,
    user_id: str,
    storage: Storage,
    content: BotContent = DEFAULT_CONTENT,
) -> OrderFlowResult:
    storage.save_flow_state(channel, user_id, ORDER_STATE_NAME, {})
    return OrderFlowResult(reply=content.order_name_prompt, handled=True, show_cancel=True)


def cancel_order_flow(
    *,
    channel: Channel,
    user_id: str,
    storage: Storage,
    content: BotContent = DEFAULT_CONTENT,
) -> OrderFlowResult:
    storage.clear_flow_state(channel, user_id)
    return OrderFlowResult(reply=content.order_cancel_text, handled=True, show_main_menu=True)


def edit_order_flow(
    *,
    channel: Channel,
    user_id: str,
    storage: Storage,
    content: BotContent = DEFAULT_CONTENT,
) -> OrderFlowResult:
    storage.save_flow_state(channel, user_id, ORDER_STATE_NAME, {})
    return OrderFlowResult(reply=content.order_edit_text, handled=True, show_cancel=True)


async def confirm_order_flow(
    *,
    channel: Channel,
    user_id: str,
    storage: Storage,
    crm: CRMSubmissionService,
    content: BotContent = DEFAULT_CONTENT,
) -> OrderFlowResult:
    state = storage.get_flow_state(channel, user_id)
    if not state or state[0] != ORDER_STATE_CONFIRM:
        return OrderFlowResult(reply=content.unknown_command_text, handled=False)

    data = state[1]
    contact = _contact_from_order_data(
        data=data,
        channel=channel,
        user_id=user_id,
        storage=storage,
    )
    if contact is None:
        storage.clear_flow_state(channel, user_id)
        return OrderFlowResult(reply=content.order_name_prompt, handled=True, show_cancel=True)

    try:
        await crm.submit_contact(contact)
    except Bitrix24NotConfiguredError:
        logger.warning("CRM is not configured; order was saved locally")
        storage.clear_flow_state(channel, user_id)
        return OrderFlowResult(
            reply=content.crm_temp_error_text,
            handled=True,
            crm_submitted=False,
            show_main_menu=True,
        )
    except Exception:
        logger.exception("Failed to submit order to CRM", extra={"channel": channel.value})
        storage.clear_flow_state(channel, user_id)
        return OrderFlowResult(
            reply=content.crm_temp_error_text,
            handled=True,
            crm_submitted=False,
            show_main_menu=True,
        )

    storage.clear_flow_state(channel, user_id)
    return OrderFlowResult(
        reply=content.crm_success_text,
        handled=True,
        crm_submitted=True,
        show_main_menu=True,
    )


async def handle_order_text(
    *,
    text: str,
    channel: Channel,
    user_id: str,
    storage: Storage,
    content: BotContent = DEFAULT_CONTENT,
) -> OrderFlowResult:
    state = storage.get_flow_state(channel, user_id)
    if not state:
        return OrderFlowResult(reply=content.unknown_command_text, handled=False)

    step, data = state
    value = text.strip()

    if step == ORDER_STATE_NAME:
        if len(value) < 2:
            return OrderFlowResult(reply=content.invalid_name_text, handled=True, show_cancel=True)
        data["name"] = value
        storage.save_flow_state(channel, user_id, ORDER_STATE_PHONE, data)
        return OrderFlowResult(reply=content.order_phone_prompt, handled=True, show_cancel=True)

    if step == ORDER_STATE_PHONE:
        digits = [char for char in value if char.isdigit()]
        if len(digits) < 10:
            return OrderFlowResult(reply=content.invalid_phone_text, handled=True, show_cancel=True)
        data["phone"] = value
        storage.save_flow_state(channel, user_id, ORDER_STATE_DETAILS, data)
        return OrderFlowResult(reply=content.order_details_prompt, handled=True, show_cancel=True)

    if step == ORDER_STATE_DETAILS:
        if len(value) < 5:
            return OrderFlowResult(reply=content.invalid_details_text, handled=True, show_cancel=True)
        data["request_details"] = value
        storage.save_flow_state(channel, user_id, ORDER_STATE_CONFIRM, data)
        return OrderFlowResult(
            reply=order_summary(
                name=data["name"],
                phone=data["phone"],
                request_details=data["request_details"],
                content=content,
            ),
            handled=True,
            show_confirm=True,
        )

    if step == ORDER_STATE_CONFIRM:
        return OrderFlowResult(reply=content.order_confirm_question, handled=True, show_confirm=True)

    storage.clear_flow_state(channel, user_id)
    return OrderFlowResult(reply=content.unknown_command_text, handled=False)


def _contact_from_order_data(
    *,
    data: dict[str, str],
    channel: Channel,
    user_id: str,
    storage: Storage,
) -> ContactData | None:
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    request_details = data.get("request_details", "").strip()
    if not name or not phone or not request_details:
        return None
    return ContactData.create(
        name=name,
        phone=phone,
        request_details=request_details,
        source_code=storage.get_source(channel, user_id),
        channel=channel,
        messenger_user_id=user_id,
    )
