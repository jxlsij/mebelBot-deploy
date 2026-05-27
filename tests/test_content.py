from mebelbot.config import Settings
from mebelbot.content import bot_content, links_text, unknown_command_reply


def test_bot_content_uses_defaults_when_not_overridden() -> None:
    content = bot_content(Settings())

    assert content.order_button == "Оформить заказ"
    assert content.catalog_button == "Каталог"


def test_bot_content_applies_known_overrides_and_ignores_unknown_keys() -> None:
    content = bot_content(
        Settings(
            BOT_CONTENT_JSON={
                "welcome_text": "Добро пожаловать",
                "contact_button": "Связаться",
                "unknown_key": "ignored",
            }
        )
    )

    assert content.welcome_text == "Добро пожаловать"
    assert content.contact_button == "Связаться"
    assert not hasattr(content, "unknown_key")


def test_links_text_uses_configured_content_copy() -> None:
    settings = Settings(
        CONTENT_LINKS_JSON={"Каталог": "https://example.org/catalog"},
        BOT_CONTENT_JSON={"links_title": "Материалы:"},
    )
    content = bot_content(settings)

    assert "Материалы:" in links_text(settings, content)


def test_unknown_command_reply_uses_configured_buttons_prompt() -> None:
    settings = Settings(
        BOT_CONTENT_JSON={
            "unknown_command_text": "Нажмите кнопку ниже.",
            "contact_prompt": "Напишите имя и телефон.",
        }
    )

    assert unknown_command_reply(bot_content(settings)) == (
        "Нажмите кнопку ниже. Напишите имя и телефон."
    )
