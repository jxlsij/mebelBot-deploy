from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import compare_digest
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mebelbot.bitrix import Bitrix24Client, DisabledBitrix24Client
from mebelbot.config import Settings, get_settings
from mebelbot.max_bot import build_max_router
from mebelbot.storage import SQLiteStorage
from mebelbot.telegram_bot import build_telegram_router, configure_telegram_webhook


class WebhookBodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int, path_prefix: str = "/webhooks/") -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.path_prefix = path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not str(scope.get("path", "")).startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return

        body_size = 0
        messages: list[Message] = []
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body_size += len(message.get("body", b""))
            if body_size > self.max_body_bytes:
                await self._send_too_large(send)
                return
            if not message.get("more_body", False):
                break

        iterator = iter(messages)

        async def replay_receive() -> Message:
            return next(iterator, {"type": "http.request", "body": b"", "more_body": False})

        await self.app(scope, replay_receive, send)

    async def _send_too_large(self, send: Send) -> None:
        body = b'{"detail":"Webhook request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def create_app(settings: Settings | None = None) -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = settings or get_settings()
    storage = SQLiteStorage(settings.database_url)
    try:
        bitrix = Bitrix24Client(settings)
    except RuntimeError:
        logging.warning("Bitrix24 is not configured; webhook app will run without CRM submission")
        bitrix = DisabledBitrix24Client()

    telegram_bot = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        if telegram_bot is not None:
            await configure_telegram_webhook(settings, telegram_bot)
        try:
            yield
        finally:
            if telegram_bot is not None:
                await telegram_bot.session.close()

    app = FastAPI(
        title="MebelBot",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_api_docs else None,
        redoc_url="/redoc" if settings.enable_api_docs else None,
        openapi_url="/openapi.json" if settings.enable_api_docs else None,
    )
    app.add_middleware(WebhookBodySizeLimitMiddleware, max_body_bytes=settings.webhook_max_body_bytes)
    trusted_hosts = _trusted_hosts(settings)
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    if settings.telegram_bot_token:
        telegram_router, telegram_bot = build_telegram_router(settings, storage, bitrix)
        app.include_router(telegram_router)

    if settings.max_bot_token and settings.webhook_secret:
        app.include_router(build_max_router(settings, storage, bitrix))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        storage.submission_status_counts()
        return {"status": "ok", "database": "ok"}

    @app.get("/ops/status")
    async def ops_status(
        x_mebelbot_admin_secret: str | None = Header(default=None),
    ) -> dict[str, bool | dict[str, int] | str]:
        if not settings.ops_status_secret:
            raise HTTPException(status_code=404, detail="Ops status endpoint is not enabled")
        if not compare_digest(x_mebelbot_admin_secret or "", settings.ops_status_secret):
            raise HTTPException(status_code=401, detail="Invalid ops status secret")

        counts = storage.submission_status_counts()
        return {
            "status": "ok",
            "database": "ok",
            "telegram_webhook_enabled": bool(
                settings.telegram_bot_token and settings.telegram_webhook_secret
            ),
            "max_webhook_enabled": bool(settings.max_bot_token and settings.webhook_secret),
            "bitrix24_configured": bool(settings.bitrix24_webhook_url),
            "crm_submissions": counts,
        }

    return app


def _trusted_hosts(settings: Settings) -> list[str]:
    configured = [host.strip() for host in settings.trusted_hosts.split(",") if host.strip()]
    if configured:
        return configured

    parsed = urlparse(settings.webhook_host)
    if not parsed.hostname:
        return []

    hosts = {parsed.hostname, "localhost", "127.0.0.1", "testserver"}
    return sorted(hosts)


app = create_app()
