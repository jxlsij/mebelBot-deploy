from __future__ import annotations

from dataclasses import dataclass, fields

from mebelbot.config import Settings


@dataclass(frozen=True)
class BotContent:
    welcome_text: str = (
        "Здравствуйте! Это Мебельное Бюро 🛋\n\n"
        "Создаем мебель под ваше пространство: кухни, шкафы, гардеробные, "
        "гостиные, спальни, детские, офисы и прихожие.\n\n"
        "Что можно сделать в боте:\n"
        "• посмотреть направления и каталог;\n"
        "• узнать больше о бюро;\n"
        "• найти контакты;\n"
        "• оставить заявку на расчет.\n\n"
        "Выберите нужный раздел в меню ниже 👇"
    )
    about_button: str = "🏛 О бюро"
    catalog_button: str = "🛋 Каталог"
    order_button: str = "📝 Оформить заказ"
    contacts_button: str = "📞 Контакты"
    qr_button: str = "🎟 Мой QR"
    main_menu_button: str = "🏠 В главное меню"
    confirm_button: str = "✅ Подтвердить"
    edit_button: str = "✏️ Изменить"
    cancel_button: str = "❌ Отменить"
    contact_button: str = "📝 Оформить заказ"
    links_button: str = "🛋 Каталог"
    about_text: str = (
        "🏛 О нашем бюро\n\n"
        "Мебельное Бюро - студия авторской и серийной мебели с 2010 года. "
        "Мы берем на себя путь от идеи и замера до производства, доставки и монтажа.\n\n"
        "✨ Что мы делаем:\n"
        "• проектируем мебель точно под размеры помещения;\n"
        "• производим кухни, шкафы, гардеробные, гостиные, спальни, детские и офисные решения;\n"
        "• подбираем материалы, фурнитуру, цветовые решения и эргономику;\n"
        "• сопровождаем проект до установки и финальной приемки.\n\n"
        "🤝 Почему нам доверяют:\n"
        "• 1200+ завершенных проектов;\n"
        "• сроки производства от 14 до 45 дней после согласования;\n"
        "• бесплатный замер и выезд дизайнера по городу;\n"
        "• гарантия 5 лет на изделия."
    )
    catalog_text: str = (
        "🛋 Каталог мебели\n\n"
        "Выберите интересующую категорию в ссылках ниже - откроются подборки с "
        "идеями, материалами и примерами решений.\n\n"
        "Не нашли нужный вариант? Оставьте заявку - изготовим мебель под ваши "
        "размеры, стиль и бюджет ✨"
    )
    contacts_text: str = (
        "📞 Контакты\n\n"
        "📍 Шоурум: г. Москва, ул. Примерная, д. 1\n"
        "🕙 Режим работы: пн-сб 10:00-20:00, вс 11:00-18:00\n\n"
        "☎️ Телефон: +7 (000) 000-00-00\n"
        "✉️ Email: hello@furniture-bureau.ru\n"
        "🌐 Сайт: https://example.com\n"
        "💬 Telegram: https://t.me/furniture_bureau\n\n"
        "Напишите нам или оставьте заявку в боте - менеджер ответит в течение "
        "15 минут в рабочее время 🙂"
    )
    order_name_prompt: str = (
        "📝 Оформление заявки\n\n"
        "Заполним короткую форму - это займет меньше минуты. После отправки "
        "менеджер уточнит детали и подготовит следующий шаг.\n\n"
        "1/3. Как вас зовут?\n"
        "Введите имя или имя + фамилию."
    )
    order_phone_prompt: str = (
        "2/3. Укажите ваш номер телефона ☎️\n"
        "Например: +7 900 123-45-67"
    )
    order_details_prompt: str = (
        "3/3. Расскажите, что вас интересует ✨\n\n"
        "Можно указать тип мебели, комнату, размеры, стиль, материалы, примерный "
        "бюджет или просто задать вопрос."
    )
    order_summary_title: str = "✅ Проверьте данные заявки:"
    order_confirm_question: str = (
        "Все верно? После подтверждения заявка уйдет менеджеру."
    )
    order_edit_text: str = "Хорошо, начнем заново ✏️\n\n1/3. Как вас зовут?"
    order_cancel_text: str = "Заявка отменена. Если передумаете - я всегда здесь 🙂"
    invalid_name_text: str = "Пожалуйста, введите корректное имя - минимум 2 символа."
    invalid_phone_text: str = (
        "Номер выглядит некорректно. Введите минимум 10 цифр, "
        "например: +7 900 123-45-67"
    )
    invalid_details_text: str = (
        "Пожалуйста, опишите пожелание чуть подробнее: например, кухня, шкаф, "
        "гардеробная или вопрос по проекту."
    )
    contact_prompt: str = (
        "Нажмите «📝 Оформить заказ», и я пошагово соберу имя, телефон и пожелание."
    )
    links_title: str = "📚 Категории каталога:"
    links_empty_text: str = (
        "Категории каталога пока не настроены. Менеджер сможет подсказать варианты в заявке."
    )
    unknown_command_text: str = (
        "Я пока не понял команду. Выберите действие в меню или начните оформление заявки."
    )
    invalid_contact_text: str = "Не распознал контакт."
    crm_success_text: str = (
        "Спасибо! Заявка принята и передана менеджеру ✅\n\n"
        "Мы свяжемся с вами в ближайшее рабочее время."
    )
    crm_temp_error_text: str = (
        "Заявку сохранили ✅\n\n"
        "CRM временно не отвечает, но мы повторим отправку и "
        "передадим данные менеджеру без повторного заполнения."
    )
    qr_caption_text: str = (
        "🎟 Ваш QR-код для приглашения в бот.\n\n"
        "Когда клиент откроет ссылку и оставит заявку, этот источник попадет в Bitrix24."
    )
    qr_unavailable_text: str = (
        "Не удалось сформировать QR-код: у Telegram-бота не найден username. "
        "Добавьте TELEGRAM_BOT_USERNAME в настройки или проверьте username бота."
    )
    qr_start_notification_text: str = (
        "🎟 По вашему QR-коду открыли бота.\n\n"
        "Пользователь: {user_name}\n"
        "Telegram ID: {user_id}\n"
        "Источник: {source}"
    )


DEFAULT_CONTENT = BotContent()

WELCOME_TEXT = DEFAULT_CONTENT.welcome_text
CONTACT_PROMPT = DEFAULT_CONTENT.contact_prompt
CRM_SUCCESS_TEXT = DEFAULT_CONTENT.crm_success_text
CRM_TEMP_ERROR_TEXT = DEFAULT_CONTENT.crm_temp_error_text
INVALID_CONTACT_TEXT = DEFAULT_CONTENT.invalid_contact_text

CONTENT_KEYS = {field.name for field in fields(BotContent)}


def bot_content(settings: Settings) -> BotContent:
    overrides = {key: value for key, value in settings.bot_content.items() if key in CONTENT_KEYS}
    return BotContent(**overrides)


def invalid_contact_reply(content: BotContent = DEFAULT_CONTENT) -> str:
    return f"{content.invalid_contact_text} {content.contact_prompt}"


def unknown_command_reply(content: BotContent = DEFAULT_CONTENT) -> str:
    return f"{content.unknown_command_text} {content.contact_prompt}"


def plain_button_label(label: str) -> str:
    value = label.strip()
    while value and not value[0].isalnum():
        value = value[1:].strip()
    return value


def command_matches(text: str, label: str) -> bool:
    value = text.strip()
    return value == label or value == plain_button_label(label)


def links_text(settings: Settings, content: BotContent = DEFAULT_CONTENT) -> str:
    if not settings.content_links:
        return content.links_empty_text
    lines = [content.catalog_text, "", content.links_title]
    lines.extend(f"• {title}: {url}" for title, url in settings.content_links.items())
    return "\n".join(lines)


def order_summary(
    *,
    name: str,
    phone: str,
    request_details: str,
    content: BotContent = DEFAULT_CONTENT,
) -> str:
    return (
        f"{content.order_summary_title}\n\n"
        f"👤 Имя: {name}\n"
        f"☎️ Телефон: {phone}\n"
        f"🛋 Пожелание:\n{request_details}\n\n"
        f"{content.order_confirm_question}"
    )


def unknown_content_keys(settings: Settings) -> list[str]:
    return sorted(key for key in settings.bot_content if key not in CONTENT_KEYS)


BOT_CONTENT_JSON_EXAMPLE = (
    '{"welcome_text":"Здравствуйте! Это Мебельное Бюро 🛋",'
    '"about_button":"🏛 О бюро","catalog_button":"🛋 Каталог","order_button":"📝 Оформить заказ",'
    '"contacts_button":"📞 Контакты","qr_button":"🎟 Мой QR","links_title":"📚 Категории каталога:",'
    '"contact_prompt":"Нажмите «📝 Оформить заказ», и я соберу данные для менеджера.",'
    '"unknown_command_text":"Выберите действие в меню.",'
    '"invalid_contact_text":"Не распознал контакт.",'
    '"crm_success_text":"Спасибо! Заявка передана менеджеру ✅",'
    '"crm_temp_error_text":"Заявку сохранили, но CRM временно не отвечает."}'
)


def parse_name_phone(message: str) -> tuple[str, str] | None:
    if "," in message:
        name, phone = message.split(",", maxsplit=1)
    else:
        parts = message.rsplit(maxsplit=1)
        if len(parts) != 2:
            return None
        name, phone = parts
    name = name.strip()
    phone = phone.strip()
    digits = [char for char in phone if char.isdigit()]
    if len(name) < 2 or len(digits) < 10:
        return None
    return name, phone
