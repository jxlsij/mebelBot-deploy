from mebelbot.config import Settings, validate_environment


def issue_pairs(settings: Settings) -> set[tuple[str, str]]:
    return {(issue.severity, issue.field) for issue in validate_environment(settings)}


def valid_settings() -> Settings:
    return Settings(
        TELEGRAM_BOT_TOKEN="1234567890:abcdefghijklmnopqrstuvwxyz",
        TELEGRAM_BOT_USERNAME="mebel_real_bot",
        MAX_BOT_TOKEN="max-token-value-with-real-length",
        MAX_BOT_USERNAME="mebel_real_max_bot",
        BITRIX24_WEBHOOK_URL="https://example.bitrix24.ru/rest/1/secret/",
        DATABASE_URL="sqlite:///data/mebelbot.sqlite3",
        WEBHOOK_HOST="https://bot.example.org",
        TELEGRAM_WEBHOOK_SECRET="telegram-secret-value",
        WEBHOOK_SECRET="secret-value-with-real-length",
        BITRIX24_SOURCE_FIELD="UF_CRM_123456",
        BITRIX24_PHONE_FIELD="PHONE",
        BITRIX24_NAME_FIELD="TITLE",
        BITRIX24_COMMENT_FIELD="COMMENTS",
        CONTENT_LINKS_JSON={"catalog": "https://example.org/catalog"},
    )


def test_validate_environment_accepts_complete_settings() -> None:
    assert validate_environment(valid_settings()) == []


def test_validate_environment_accepts_cloudflare_worker_api_base() -> None:
    settings = valid_settings().model_copy(
        update={
            "telegram_api_base": "https://telegram-proxy.example.workers.dev",
            "telegram_webhook_secret": "telegram-secret-value",
        }
    )

    assert validate_environment(settings) == []


def test_validate_environment_accepts_legacy_telebot_api_url_format() -> None:
    settings = valid_settings().model_copy(
        update={
            "telegram_api_base": "https://telegram-proxy.example.workers.dev/bot{0}/{1}",
        }
    )

    assert validate_environment(settings) == []


def test_validate_environment_flags_missing_required_values() -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="",
        TELEGRAM_BOT_USERNAME="",
        MAX_BOT_TOKEN="change-me",
        MAX_BOT_USERNAME="",
        BITRIX24_WEBHOOK_URL="",
        DATABASE_URL="postgresql://db",
        WEBHOOK_HOST="http://example.com",
        WEBHOOK_SECRET="change-me",
        BITRIX24_SOURCE_FIELD="UF_CRM_SPEAKER_SOURCE",
    )

    issues = issue_pairs(settings)

    assert ("error", "TELEGRAM_BOT_TOKEN") in issues
    assert ("warning", "MAX_BOT_TOKEN") in issues
    assert ("warning", "BITRIX24_WEBHOOK_URL") in issues
    assert ("error", "DATABASE_URL") in issues
    assert ("error", "WEBHOOK_HOST") in issues
    assert ("warning", "TELEGRAM_BOT_USERNAME") in issues
    assert ("warning", "MAX_BOT_USERNAME") in issues
    assert ("warning", "BITRIX24_SOURCE_FIELD") in issues


def test_validate_environment_requires_max_secret_when_max_is_configured() -> None:
    settings = valid_settings().model_copy(update={"webhook_secret": "", "max_bot_token": "max-token"})

    issues = issue_pairs(settings)

    assert ("error", "WEBHOOK_SECRET") in issues


def test_validate_environment_requires_telegram_webhook_secret_for_webhook_mode() -> None:
    settings = valid_settings().model_copy(update={"telegram_webhook_secret": ""})

    issues = issue_pairs(settings)

    assert ("error", "TELEGRAM_WEBHOOK_SECRET") in issues


def test_validate_environment_requires_valid_bitrix_url_when_crm_is_configured() -> None:
    settings = valid_settings().model_copy(update={"bitrix24_webhook_url": "not a url"})

    issues = issue_pairs(settings)

    assert ("error", "BITRIX24_WEBHOOK_URL") in issues


def test_validate_environment_flags_invalid_content_links() -> None:
    settings = valid_settings().model_copy(update={"content_links": {"catalog": "ftp://bad"}})

    issues = validate_environment(settings)

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].field == "CONTENT_LINKS_JSON"


def test_validate_environment_flags_invalid_telegram_api_base() -> None:
    settings = valid_settings().model_copy(update={"telegram_api_base": "not a url"})

    issues = validate_environment(settings)

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].field == "TELEGRAM_API_BASE"


def test_validate_environment_rejects_tiny_webhook_body_limit() -> None:
    settings = valid_settings().model_copy(update={"webhook_max_body_bytes": 100})

    issues = issue_pairs(settings)

    assert ("error", "WEBHOOK_MAX_BODY_BYTES") in issues


def test_validate_environment_checks_optional_ops_status_secret() -> None:
    settings = valid_settings().model_copy(update={"ops_status_secret": "short"})

    issues = issue_pairs(settings)

    assert ("warning", "OPS_STATUS_SECRET") in issues
