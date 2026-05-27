from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class EnvironmentIssue:
    severity: Literal["error", "warning"]
    field: str
    message: str


class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(default="", alias="TELEGRAM_BOT_USERNAME")
    telegram_api_base: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_API_BASE", "TELEGRAM_API_URL"),
    )
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    max_bot_token: str = Field(default="", alias="MAX_BOT_TOKEN")
    max_bot_username: str = Field(default="", alias="MAX_BOT_USERNAME")
    max_bot_qr_image_url: str = Field(default="", alias="MAX_BOT_QR_IMAGE_URL")
    bitrix24_webhook_url: str = Field(default="", alias="BITRIX24_WEBHOOK_URL")
    database_url: str = Field(default="sqlite:///data/mebelbot.sqlite3", alias="DATABASE_URL")
    webhook_host: str = Field(default="", alias="WEBHOOK_HOST")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    ops_status_secret: str = Field(default="", alias="OPS_STATUS_SECRET")
    enable_api_docs: bool = Field(default=False, alias="ENABLE_API_DOCS")
    webhook_max_body_bytes: int = Field(default=262_144, alias="WEBHOOK_MAX_BODY_BYTES")
    trusted_hosts: str = Field(default="", alias="TRUSTED_HOSTS")

    bitrix24_entity: Literal["lead", "deal"] = Field(default="lead", alias="BITRIX24_ENTITY")
    bitrix24_source_field: str = Field(
        default="UF_CRM_SPEAKER_SOURCE",
        alias="BITRIX24_SOURCE_FIELD",
    )
    bitrix24_phone_field: str = Field(default="PHONE", alias="BITRIX24_PHONE_FIELD")
    bitrix24_name_field: str = Field(default="TITLE", alias="BITRIX24_NAME_FIELD")
    bitrix24_comment_field: str = Field(default="COMMENTS", alias="BITRIX24_COMMENT_FIELD")
    content_links: dict[str, str] = Field(default_factory=dict, alias="CONTENT_LINKS_JSON")
    bot_content: dict[str, str] = Field(default_factory=dict, alias="BOT_CONTENT_JSON")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("content_links", mode="before")
    @classmethod
    def parse_content_links(cls, value: object) -> dict[str, str]:
        return parse_json_string_map(value, field_name="CONTENT_LINKS_JSON")

    @field_validator("bot_content", mode="before")
    @classmethod
    def parse_bot_content(cls, value: object) -> dict[str, str]:
        return parse_json_string_map(value, field_name="BOT_CONTENT_JSON")

    def require_telegram(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    def require_telegram_webhook(self) -> None:
        self.require_telegram()
        if not self.telegram_webhook_secret:
            raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is required for Telegram webhooks")

    def require_max(self) -> None:
        if not self.max_bot_token:
            raise RuntimeError("MAX_BOT_TOKEN is required")
        if not self.webhook_secret:
            raise RuntimeError("WEBHOOK_SECRET is required for Max webhooks")

    def require_bitrix(self) -> None:
        if not self.bitrix24_webhook_url or not self.bitrix24_webhook_url.startswith(("http://", "https://")):
            raise RuntimeError("BITRIX24_WEBHOOK_URL must be a valid http(s) URL")


def parse_json_string_map(value: object, *, field_name: str) -> dict[str, str]:
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return {str(key): str(link) for key, link in value.items()}
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError(f"{field_name} must be a JSON object")
            return {str(key): str(link) for key, link in parsed.items()}
        raise ValueError(f"{field_name} must be a JSON object")


def validate_environment(settings: Settings) -> list[EnvironmentIssue]:
    issues: list[EnvironmentIssue] = []

    def add(severity: Literal["error", "warning"], field: str, message: str) -> None:
        issues.append(EnvironmentIssue(severity=severity, field=field, message=message))

    def missing_or_placeholder(value: str, *, placeholder_prefixes: tuple[str, ...] = ()) -> bool:
        normalized = value.strip().lower()
        if not normalized:
            return True
        placeholders = {
            "change-me",
            "changeme",
            "example",
            "example.com",
            "your-token",
            "your_tg_bot",
            "your_max_bot",
        }
        if normalized in placeholders:
            return True
        if "example.com" in normalized:
            return True
        return any(normalized.startswith(prefix) for prefix in placeholder_prefixes)

    def require_secret(field: str, value: str, *, min_length: int = 1) -> None:
        if missing_or_placeholder(value, placeholder_prefixes=("your_", "your-", "token")):
            add("error", field, "set a real value in .env")
        elif len(value.strip()) < min_length:
            add("warning", field, f"value looks short; expected at least {min_length} characters")

    def require_url(field: str, value: str, *, https_only: bool = False) -> None:
        if missing_or_placeholder(value):
            add("error", field, "set a real URL in .env")
            return
        parsed = urlparse(value)
        allowed_schemes = ("https",) if https_only else ("http", "https")
        if parsed.scheme not in allowed_schemes or not parsed.netloc:
            scheme = "HTTPS" if https_only else "HTTP or HTTPS"
            add("error", field, f"must be a valid {scheme} URL")
        elif parsed.scheme != "https":
            add("warning", field, "use HTTPS in production")

    require_secret("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token, min_length=20)
    max_configured = not missing_or_placeholder(
        settings.max_bot_token,
        placeholder_prefixes=("your_", "your-", "token"),
    )
    bitrix_configured = not missing_or_placeholder(
        settings.bitrix24_webhook_url,
        placeholder_prefixes=("your_", "your-"),
    )

    if max_configured:
        require_secret("MAX_BOT_TOKEN", settings.max_bot_token, min_length=20)
    else:
        add("warning", "MAX_BOT_TOKEN", "set it only if Max webhooks will be deployed")
    if bitrix_configured:
        require_url("BITRIX24_WEBHOOK_URL", settings.bitrix24_webhook_url)
    else:
        add("warning", "BITRIX24_WEBHOOK_URL", "CRM is disabled until a real Bitrix24 webhook is set")
    require_url("WEBHOOK_HOST", settings.webhook_host, https_only=True)
    telegram_webhook_configured = bool(
        settings.telegram_bot_token.strip() and settings.webhook_host.strip()
    )
    if telegram_webhook_configured:
        require_secret("TELEGRAM_WEBHOOK_SECRET", settings.telegram_webhook_secret, min_length=16)
    elif settings.telegram_webhook_secret and len(settings.telegram_webhook_secret.strip()) < 16:
        add(
            "warning",
            "TELEGRAM_WEBHOOK_SECRET",
            "value looks short; expected at least 16 characters",
        )
    if max_configured:
        require_secret("WEBHOOK_SECRET", settings.webhook_secret, min_length=16)
    elif settings.webhook_secret and not missing_or_placeholder(
        settings.webhook_secret,
        placeholder_prefixes=("your_", "your-", "token"),
    ):
        require_secret("WEBHOOK_SECRET", settings.webhook_secret, min_length=16)
    if settings.ops_status_secret:
        require_secret("OPS_STATUS_SECRET", settings.ops_status_secret, min_length=16)

    if missing_or_placeholder(settings.telegram_bot_username, placeholder_prefixes=("your_",)):
        add("warning", "TELEGRAM_BOT_USERNAME", "set it before generating Telegram QR links")
    if settings.telegram_api_base:
        api_base = settings.telegram_api_base.replace("/bot{0}/{1}", "").rstrip("/")
        parsed = urlparse(api_base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            add(
                "error",
                "TELEGRAM_API_BASE",
                "must be a valid HTTP or HTTPS Cloudflare Worker/base API URL",
            )
        elif parsed.scheme != "https":
            add("warning", "TELEGRAM_API_BASE", "use HTTPS in production")
    if missing_or_placeholder(settings.max_bot_username, placeholder_prefixes=("your_",)):
        add("warning", "MAX_BOT_USERNAME", "set it before generating Max QR links")

    if settings.webhook_max_body_bytes < 1024:
        add("error", "WEBHOOK_MAX_BODY_BYTES", "must be at least 1024 bytes")

    if not settings.database_url.startswith("sqlite:///"):
        add("error", "DATABASE_URL", "only sqlite:/// URLs are supported by this runtime")
    else:
        database_path = settings.database_url.removeprefix("sqlite:///").strip()
        if not database_path:
            add("error", "DATABASE_URL", "SQLite path must not be empty")
        elif Path(database_path).suffix == "":
            add("warning", "DATABASE_URL", "SQLite path does not look like a database file")

    crm_fields = {
        "BITRIX24_SOURCE_FIELD": settings.bitrix24_source_field,
        "BITRIX24_PHONE_FIELD": settings.bitrix24_phone_field,
        "BITRIX24_NAME_FIELD": settings.bitrix24_name_field,
        "BITRIX24_COMMENT_FIELD": settings.bitrix24_comment_field,
    }
    for field, value in crm_fields.items():
        if bitrix_configured and missing_or_placeholder(value):
            add("error", field, "set the real Bitrix24 field code")

    if settings.bitrix24_source_field == "UF_CRM_SPEAKER_SOURCE":
        add(
            "warning",
            "BITRIX24_SOURCE_FIELD",
            "default placeholder is still configured; replace it with the real UF_CRM_* field",
        )

    for title, link in settings.content_links.items():
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            add("error", "CONTENT_LINKS_JSON", f"link for {title!r} must be an HTTP or HTTPS URL")

    return issues


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
