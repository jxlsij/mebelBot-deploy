from __future__ import annotations

import asyncio
from secrets import compare_digest

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, KeyboardButton, Message, ReplyKeyboardMarkup, Update
from fastapi import APIRouter, Header, HTTPException, Request

from mebelbot.config import Settings
from mebelbot.content import bot_content, invalid_contact_reply, links_text
from mebelbot.crm import BitrixClient, CRMSubmissionService
from mebelbot.domain import Channel, parse_start_payload
from mebelbot.flow import (
    cancel_order_flow,
    confirm_order_flow,
    edit_order_flow,
    handle_contact_text,
    handle_order_text,
    start_order_flow,
)
from mebelbot.qr import qr_png_bytes, telegram_link, validate_bot_username
from mebelbot.storage import Storage


def main_menu(content) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=content.about_button), KeyboardButton(text=content.catalog_button)],
            [KeyboardButton(text=content.order_button), KeyboardButton(text=content.contacts_button)],
            [KeyboardButton(text=content.qr_button)],
        ],
        resize_keyboard=True,
    )


def cancel_menu(content) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=content.cancel_button)]],
        resize_keyboard=True,
    )


def confirm_menu(content) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=content.confirm_button), KeyboardButton(text=content.edit_button)],
            [KeyboardButton(text=content.cancel_button)],
        ],
        resize_keyboard=True,
    )


def markup_for_result(result, content):
    if result.show_confirm:
        return confirm_menu(content)
    if result.show_cancel:
        return cancel_menu(content)
    return main_menu(content)


def telegram_qr_source(storage: Storage, user_id: str) -> str:
    existing_source = storage.get_source(Channel.telegram, user_id)
    if existing_source:
        return existing_source
    source = f"tg_{user_id}"
    storage.save_source(Channel.telegram, user_id, source)
    return source


async def telegram_bot_username(message: Message, settings: Settings) -> str | None:
    if settings.telegram_bot_username:
        return validate_bot_username(settings.telegram_bot_username, field_name="TELEGRAM_BOT_USERNAME")

    bot_user = await message.bot.get_me()
    if not bot_user.username:
        return None
    return validate_bot_username(bot_user.username, field_name="Telegram bot username")


def build_dispatcher(settings: Settings, storage: Storage, bitrix: BitrixClient) -> Dispatcher:
    dp = Dispatcher()
    crm = CRMSubmissionService(storage, bitrix)
    content = bot_content(settings)
    reply_markup = main_menu(content)

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        source = parse_start_payload(message.text)
        if source and message.from_user:
            storage.save_source(Channel.telegram, str(message.from_user.id), source)
            storage.clear_flow_state(Channel.telegram, str(message.from_user.id))
        await message.answer(content.welcome_text, reply_markup=reply_markup)

    @dp.message(F.text == content.main_menu_button)
    async def on_main_menu(message: Message) -> None:
        if message.from_user:
            storage.clear_flow_state(Channel.telegram, str(message.from_user.id))
        await message.answer(content.welcome_text, reply_markup=reply_markup)

    @dp.message(F.text == content.about_button)
    async def on_about(message: Message) -> None:
        await message.answer(content.about_text, reply_markup=reply_markup)

    @dp.message((F.text == content.catalog_button) | (F.text == content.links_button))
    async def on_links(message: Message) -> None:
        await message.answer(links_text(settings, content), reply_markup=reply_markup)

    @dp.message(F.text == content.contacts_button)
    async def on_contacts(message: Message) -> None:
        await message.answer(content.contacts_text, reply_markup=reply_markup)

    @dp.message(F.text == content.qr_button)
    async def on_qr(message: Message) -> None:
        if not message.from_user:
            await message.answer(content.qr_unavailable_text, reply_markup=reply_markup)
            return

        try:
            username = await telegram_bot_username(message, settings)
        except ValueError:
            username = None
        if not username:
            await message.answer(content.qr_unavailable_text, reply_markup=reply_markup)
            return

        source = telegram_qr_source(storage, str(message.from_user.id))
        link = telegram_link(username, source)
        qr_file = BufferedInputFile(qr_png_bytes(link), filename=f"{source}-telegram.png")
        await message.answer_photo(
            qr_file,
            caption=f"{content.qr_caption_text}\n\nСсылка: {link}\nИсточник: {source}",
            reply_markup=reply_markup,
        )

    @dp.message((F.text == content.order_button) | (F.text == content.contact_button))
    async def on_contact_button(message: Message) -> None:
        if not message.from_user:
            await message.answer(invalid_contact_reply(content), reply_markup=reply_markup)
            return
        result = start_order_flow(
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            content=content,
        )
        await message.answer(result.reply, reply_markup=markup_for_result(result, content))

    @dp.message(F.text == content.cancel_button)
    async def on_cancel(message: Message) -> None:
        if not message.from_user:
            await message.answer(content.order_cancel_text, reply_markup=reply_markup)
            return
        result = cancel_order_flow(
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            content=content,
        )
        await message.answer(result.reply, reply_markup=markup_for_result(result, content))

    @dp.message(F.text == content.edit_button)
    async def on_edit(message: Message) -> None:
        if not message.from_user:
            await message.answer(content.order_edit_text, reply_markup=reply_markup)
            return
        result = edit_order_flow(
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            content=content,
        )
        await message.answer(result.reply, reply_markup=markup_for_result(result, content))

    @dp.message(F.text == content.confirm_button)
    async def on_confirm(message: Message) -> None:
        if not message.from_user:
            await message.answer(invalid_contact_reply(content), reply_markup=reply_markup)
            return
        result = await confirm_order_flow(
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            crm=crm,
            content=content,
        )
        await message.answer(result.reply, reply_markup=markup_for_result(result, content))

    @dp.message(F.text)
    async def on_text(message: Message) -> None:
        if not message.from_user:
            await message.answer(invalid_contact_reply(content), reply_markup=reply_markup)
            return

        order_result = await handle_order_text(
            text=message.text or "",
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            content=content,
        )
        if order_result.handled:
            await message.answer(
                order_result.reply,
                reply_markup=markup_for_result(order_result, content),
            )
            return

        result = await handle_contact_text(
            text=message.text or "",
            channel=Channel.telegram,
            user_id=str(message.from_user.id),
            storage=storage,
            crm=crm,
            content=content,
        )
        await message.answer(result.reply, reply_markup=reply_markup)

    return dp


def _normalize_telegram_api_base(value: str) -> str:
    return value.replace("/bot{0}/{1}", "").rstrip("/")


def build_bot(settings: Settings) -> Bot:
    settings.require_telegram()
    if settings.telegram_api_base:
        api = TelegramAPIServer.from_base(_normalize_telegram_api_base(settings.telegram_api_base))
        return Bot(token=settings.telegram_bot_token, session=AiohttpSession(api=api))
    return Bot(token=settings.telegram_bot_token)


def build_telegram_router(
    settings: Settings,
    storage: Storage,
    bitrix: BitrixClient,
) -> tuple[APIRouter, Bot]:
    settings.require_telegram_webhook()
    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings, storage, bitrix)
    router = APIRouter()

    @router.post("/webhooks/telegram")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        if not compare_digest(
            x_telegram_bot_api_secret_token or "",
            settings.telegram_webhook_secret,
        ):
            raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")

        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"status": "ok"}

    return router, bot


async def configure_telegram_webhook(settings: Settings, bot: Bot) -> None:
    if not settings.webhook_host:
        return

    webhook_url = f"{settings.webhook_host.rstrip('/')}/webhooks/telegram"
    await bot.set_webhook(
        webhook_url,
        secret_token=settings.telegram_webhook_secret or None,
        drop_pending_updates=True,
    )


async def run_telegram(settings: Settings, storage: Storage, bitrix: BitrixClient) -> None:
    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings, storage, bitrix)
    await dispatcher.start_polling(bot)


def run_telegram_sync(settings: Settings, storage: Storage, bitrix: BitrixClient) -> None:
    asyncio.run(run_telegram(settings, storage, bitrix))
