"""
Мебельное Бюро — Telegram-бот для клиентов.
Запуск: python furniture_bot.py
Нужно задать BOT_TOKEN (получить у @BotFather).
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # Demo only: set through environment.

# ─── Состояния FSM для оформления заказа ───────────────────────────────────

class OrderForm(StatesGroup):
    name = State()
    phone = State()
    wish = State()
    confirm = State()


# ─── Клавиатуры ────────────────────────────────────────────────────────────

def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏛  О бюро",    callback_data="about"),
            InlineKeyboardButton(text="📖  Каталог",   callback_data="catalog"),
        ],
        [
            InlineKeyboardButton(text="🛒  Оформить заказ", callback_data="order"),
            InlineKeyboardButton(text="📞  Контакты",       callback_data="contacts"),
        ],
    ])


def kb_catalog():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛋  Гостиные",         url="https://example.com/catalog/living"),
            InlineKeyboardButton(text="🛏  Спальни",          url="https://example.com/catalog/bedroom"),
        ],
        [
            InlineKeyboardButton(text="🍳  Кухни",            url="https://example.com/catalog/kitchen"),
            InlineKeyboardButton(text="🎠  Детские",          url="https://example.com/catalog/kids"),
        ],
        [
            InlineKeyboardButton(text="💼  Офисная мебель",   url="https://example.com/catalog/office"),
            InlineKeyboardButton(text="🚪  Прихожие",         url="https://example.com/catalog/hallway"),
        ],
        [
            InlineKeyboardButton(text="📄  Полный каталог PDF", url="https://example.com/catalog/full.pdf"),
        ],
        [
            InlineKeyboardButton(text="↩️  В главное меню", callback_data="main_menu"),
        ],
    ])


def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️  В главное меню", callback_data="main_menu")],
    ])


def kb_order_confirm():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅  Подтвердить",  callback_data="order_yes"),
            InlineKeyboardButton(text="✏️  Изменить",     callback_data="order_edit"),
        ],
        [
            InlineKeyboardButton(text="❌  Отменить заказ", callback_data="order_cancel"),
        ],
    ])


def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌  Отменить", callback_data="order_cancel")],
    ])


# ─── Тексты ────────────────────────────────────────────────────────────────

WELCOME_TEXT = (
    "✨ <b>Приветствую вас в Мебельном Бюро!</b>\n\n"
    "Мы создаём пространство, в котором хочется жить.\n"
    "Каждый предмет — это история, рассказанная деревом, металлом и тканью.\n\n"
    "Чем могу вам помочь?"
)

ABOUT_TEXT = (
    "🏛 <b>О нашем бюро</b>\n\n"
    "«Мебельное Бюро» — студия авторской и серийной мебели с 2010 года.\n\n"
    "🔹 <b>Что мы делаем</b>\n"
    "Проектируем и производим мебель для жилых и коммерческих пространств: "
    "от кухонного гарнитура до полной меблировки офиса или ресторана.\n\n"
    "🔹 <b>Наши принципы</b>\n"
    "• Только сертифицированные материалы\n"
    "• Точные сроки производства (от 14 до 45 дней)\n"
    "• Бесплатный замер и выезд дизайнера\n"
    "• Гарантия 5 лет на все изделия\n\n"
    "🔹 <b>Цифры</b>\n"
    "• <b>1 200+</b> завершённых проектов\n"
    "• <b>14</b> лет на рынке\n"
    "• <b>4.9 ★</b> — средняя оценка клиентов\n\n"
    "Хотите узнать больше или сразу к делу? 👇"
)

CONTACTS_TEXT = (
    "📞 <b>Контакты</b>\n\n"
    "🏠 <b>Шоурум:</b> г. Москва, ул. Примерная, д. 1\n"
    "🕐 <b>Режим работы:</b> пн–сб 10:00–20:00, вс 11:00–18:00\n\n"
    "📱 <b>Телефон:</b> <a href='tel:+70000000000'>+7 (000) 000-00-00</a>\n"
    "📧 <b>Email:</b> hello@furniture-bureau.ru\n"
    "🌐 <b>Сайт:</b> <a href='https://example.com'>furniture-bureau.ru</a>\n\n"
    "💬 <b>Мессенджеры:</b>\n"
    "• <a href='https://t.me/furniture_bureau'>Telegram</a>\n"
    "• <a href='https://wa.me/70000000000'>WhatsApp</a>\n\n"
    "<i>Напишите нам — ответим в течение 15 минут в рабочее время.</i>"
)


# ─── Хэндлеры ──────────────────────────────────────────────────────────────

async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=kb_main(), parse_mode="HTML")


async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=kb_main(), parse_mode="HTML")
    await callback.answer()


async def cb_about(callback: CallbackQuery):
    await callback.message.edit_text(
        ABOUT_TEXT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖  Посмотреть каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="🛒  Оформить заказ",      callback_data="order")],
            [InlineKeyboardButton(text="↩️  В главное меню",     callback_data="main_menu")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


async def cb_catalog(callback: CallbackQuery):
    text = (
        "📖 <b>Каталог мебели</b>\n\n"
        "Выберите интересующую вас категорию — откроется полная коллекция "
        "с фотографиями, размерами и ценами.\n\n"
        "<i>Не нашли нужное? Мы изготовим под ваши параметры.</i>"
    )
    await callback.message.edit_text(text, reply_markup=kb_catalog(), parse_mode="HTML")
    await callback.answer()


async def cb_contacts(callback: CallbackQuery):
    await callback.message.edit_text(CONTACTS_TEXT, reply_markup=kb_back(), parse_mode="HTML")
    await callback.answer()


# ─── Оформление заказа (FSM) ───────────────────────────────────────────────

async def cb_order_start(callback: CallbackQuery, state: FSMContext):
    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        "Отлично! Заполним небольшую форму — это займёт меньше минуты.\n\n"
        "<b>Шаг 1 из 3</b> · Как вас зовут?\n\n"
        "<i>Введите имя или имя + фамилию</i>"
    )
    await state.set_state(OrderForm.name)
    await callback.message.edit_text(text, reply_markup=kb_cancel(), parse_mode="HTML")
    await callback.answer()


async def order_get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя (минимум 2 символа).")
        return
    await state.update_data(name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(
        f"Приятно познакомиться, <b>{name}</b>! 👋\n\n"
        "<b>Шаг 2 из 3</b> · Укажите ваш номер телефона\n\n"
        "<i>Например: +7 900 000-00-00</i>",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )


async def order_get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 10:
        await message.answer(
            "Номер выглядит некорректно. Введите телефон, например: <code>+7 900 123-45-67</code>",
            parse_mode="HTML",
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.wish)
    await message.answer(
        "<b>Шаг 3 из 3</b> · Расскажите, что вас интересует\n\n"
        "<i>Опишите желаемую мебель, стиль, примерный бюджет или задайте вопрос — "
        "чем подробнее, тем точнее мы сможем помочь.</i>",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )


async def order_get_wish(message: Message, state: FSMContext):
    wish = message.text.strip()
    if len(wish) < 5:
        await message.answer("Пожалуйста, опишите пожелание чуть подробнее.")
        return
    await state.update_data(wish=wish)
    data = await state.get_data()
    await state.set_state(OrderForm.confirm)

    summary = (
        "📋 <b>Проверьте данные заявки:</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Телефон:</b> {data['phone']}\n"
        f"💬 <b>Пожелание:</b>\n{data['wish']}\n\n"
        "Всё верно? Наш менеджер свяжется с вами в течение 15 минут."
    )
    await message.answer(summary, reply_markup=kb_order_confirm(), parse_mode="HTML")


async def order_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    # Здесь в реальном проекте — отправка данных в CRM / менеджеру / БД
    # Например: await bot.send_message(MANAGER_CHAT_ID, ...)

    await callback.message.edit_text(
        "🎉 <b>Заявка принята!</b>\n\n"
        f"Спасибо, <b>{data['name']}</b>! Мы получили вашу заявку и\n"
        "свяжемся с вами по номеру <b>{phone}</b> в ближайшее время.\n\n"
        "<i>Пока ждёте — загляните в наш каталог 😊</i>".format(phone=data['phone']),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖  Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="↩️  В главное меню", callback_data="main_menu")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer("Заявка отправлена!", show_alert=False)


async def order_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(OrderForm.name)
    await callback.message.edit_text(
        "✏️ Начнём заново.\n\n"
        "<b>Шаг 1 из 3</b> · Как вас зовут?",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


async def order_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Заявка отменена. Если передумаете — я всегда здесь 😊",
        reply_markup=kb_main(),
        parse_mode="HTML",
    )
    await callback.answer("Отменено")


# ─── Запуск ────────────────────────────────────────────────────────────────

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # /start
    dp.message.register(cmd_start, CommandStart())

    # Главное меню
    dp.callback_query.register(cb_main_menu, F.data == "main_menu")
    dp.callback_query.register(cb_about,     F.data == "about")
    dp.callback_query.register(cb_catalog,   F.data == "catalog")
    dp.callback_query.register(cb_contacts,  F.data == "contacts")

    # Заказ — запуск
    dp.callback_query.register(cb_order_start, F.data == "order")

    # Заказ — шаги FSM
    dp.message.register(order_get_name,  OrderForm.name)
    dp.message.register(order_get_phone, OrderForm.phone)
    dp.message.register(order_get_wish,  OrderForm.wish)

    # Заказ — подтверждение/редактирование/отмена
    dp.callback_query.register(order_confirm, F.data == "order_yes")
    dp.callback_query.register(order_edit,    F.data == "order_edit")
    dp.callback_query.register(order_cancel,  F.data == "order_cancel")

    print("🚀 Бот Мебельного Бюро запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
