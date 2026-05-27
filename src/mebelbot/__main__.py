from __future__ import annotations

import argparse
import asyncio
import logging

import httpx

from mebelbot.bitrix import Bitrix24Client, DisabledBitrix24Client
from mebelbot.config import EnvironmentIssue, Settings, get_settings, validate_environment
from mebelbot.crm import CRMSubmissionService
from mebelbot.domain import Channel, ContactData
from mebelbot.max_bot import MaxClient
from mebelbot.storage import SQLiteStorage
from mebelbot.telegram_bot import run_telegram_sync


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Run MebelBot services")
    parser.add_argument(
        "service",
        choices=[
            "telegram",
            "max-subscribe",
            "retry-failed-crm",
            "validate-env",
            "bitrix-validate-fields",
            "bitrix-smoke-test",
        ],
        help=(
            "Run Telegram polling, register the Max webhook subscription, "
            "retry failed CRM submissions, validate .env values, validate Bitrix24 field mappings, "
            "or create a test Bitrix24 CRM item."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of failed CRM submissions to retry.",
    )
    parser.add_argument(
        "--source",
        default="smoke_test_source",
        help="Speaker/source code to send during the Bitrix24 smoke test.",
    )
    parser.add_argument(
        "--phone",
        default="+10000000000",
        help="Phone number to send during the Bitrix24 smoke test.",
    )
    parser.add_argument(
        "--name",
        default="MebelBot Smoke Test",
        help="Client name to send during the Bitrix24 smoke test.",
    )
    args = parser.parse_args()

    settings = get_settings()

    if args.service == "telegram":
        storage = SQLiteStorage(settings.database_url)
        bitrix = _bitrix_for_optional_crm(settings)
        run_telegram_sync(settings, storage, bitrix)
    elif args.service == "max-subscribe":
        settings.require_max()
        if not settings.webhook_host or not settings.webhook_host.startswith("https://"):
            raise RuntimeError("WEBHOOK_HOST must be an HTTPS URL for Max production webhooks")
        webhook_url = f"{settings.webhook_host.rstrip('/')}/webhooks/max"
        result = asyncio.run(MaxClient(settings.max_bot_token).subscribe_webhook(
            webhook_url,
            settings.webhook_secret,
        ))
        print(result)
    elif args.service == "retry-failed-crm":
        storage = SQLiteStorage(settings.database_url)
        bitrix = Bitrix24Client(settings)
        result = asyncio.run(
            CRMSubmissionService(storage, bitrix).retry_failed_submissions(limit=args.limit)
        )
        print(
            "CRM retry complete: "
            f"attempted={result.attempted} succeeded={result.succeeded} failed={result.failed}"
        )
        if result.failed:
            raise SystemExit(1)
    elif args.service == "validate-env":
        issues = validate_environment(settings)
        if not issues:
            print("Environment validation passed.")
            return

        print("Environment validation found issues:")
        for issue in issues:
            print(_format_environment_issue(issue))

        if any(issue.severity == "error" for issue in issues):
            raise SystemExit(1)
    elif args.service == "bitrix-validate-fields":
        try:
            bitrix = Bitrix24Client(settings)
            result = asyncio.run(_run_bitrix_field_validation(bitrix, settings))
        except (RuntimeError, httpx.HTTPError) as error:
            raise SystemExit(f"error: {_format_exception(error)}") from None
        print(result)
    elif args.service == "bitrix-smoke-test":
        try:
            bitrix = Bitrix24Client(settings)
            result = asyncio.run(
                _run_bitrix_smoke_test(bitrix, settings, args.name, args.phone, args.source)
            )
        except (RuntimeError, httpx.HTTPError) as error:
            raise SystemExit(f"error: {_format_exception(error)}") from None
        print(result)


def _format_environment_issue(issue: EnvironmentIssue) -> str:
    marker = "ERROR" if issue.severity == "error" else "WARN"
    return f"- {marker} {issue.field}: {issue.message}"


def _format_exception(error: Exception) -> str:
    message = str(error).strip()
    if message:
        return message
    return type(error).__name__


def _bitrix_for_optional_crm(settings: Settings) -> Bitrix24Client | DisabledBitrix24Client:
    try:
        return Bitrix24Client(settings)
    except RuntimeError:
        logging.warning("Bitrix24 is not configured; Telegram bot will run without CRM submission")
        return DisabledBitrix24Client()


async def _run_bitrix_smoke_test(
    bitrix: Bitrix24Client,
    settings: Settings,
    name: str,
    phone: str,
    source: str,
) -> str:
    contact = ContactData.create(
        name=name,
        phone=phone,
        source_code=source,
        channel=Channel.telegram,
        messenger_user_id="bitrix-smoke-test",
    )
    item_id = await bitrix.create_crm_item(contact)
    item = await bitrix.get_crm_item(item_id)
    fields = item.get("result")
    if not isinstance(fields, dict):
        raise RuntimeError("Bitrix24 get response did not contain a CRM item")

    actual_source = fields.get(settings.bitrix24_source_field)
    if actual_source != source:
        raise RuntimeError(
            "Bitrix24 smoke test created the CRM item, but source field did not match: "
            f"entity={settings.bitrix24_entity} id={item_id} "
            f"field={settings.bitrix24_source_field} expected={source!r} actual={actual_source!r}"
        )

    return (
        "Bitrix24 smoke test passed: "
        f"entity={settings.bitrix24_entity} id={item_id} "
        f"source_field={settings.bitrix24_source_field} source={source}"
    )


async def _run_bitrix_field_validation(bitrix: Bitrix24Client, settings: Settings) -> str:
    fields = await bitrix.get_crm_fields()
    required_fields = {
        "source": settings.bitrix24_source_field,
        "phone": settings.bitrix24_phone_field,
        "name": settings.bitrix24_name_field,
        "comment": settings.bitrix24_comment_field,
    }
    missing = [field for field in required_fields.values() if field not in fields]
    if missing:
        raise RuntimeError(
            "Bitrix24 field validation failed: "
            f"entity={settings.bitrix24_entity} missing={', '.join(missing)}"
        )

    mapped = ", ".join(f"{purpose}={field}" for purpose, field in required_fields.items())
    return f"Bitrix24 field validation passed: entity={settings.bitrix24_entity} {mapped}"


if __name__ == "__main__":
    main()
