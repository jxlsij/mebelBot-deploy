# Инструкция для ИИ: GitHub + HuggingFace Docker Space деплой Telegram-бота

Ты — ИИ-ассистент в локальном проекте. Твоя задача — подготовить проект к
публичному GitHub-репозиторию, создать новый HuggingFace Space, задеплоить бот и
проверить, что он реально запущен.

Эта инструкция подходит для пакетных Python-проектов на FastAPI/ASGI/aiogram,
а не только для простого `main.py` на `telebot`.

## Контекст

HuggingFace Spaces на бесплатном тарифе может блокировать прямые исходящие
запросы к `api.telegram.org`. Поэтому Telegram Bot API лучше вызывать через
Cloudflare Worker-прокси.

Правильная production-схема:

- GitHub хранит исходный код.
- HuggingFace Space с Docker runtime запускает приложение на порту `7860`.
- Приложение принимает Telegram webhook, например `POST /webhooks/telegram`.
- Приложение на старте регистрирует webhook в Telegram.
- Cloudflare Worker проксирует запросы приложения к Telegram Bot API.
- Secrets не попадают в Git.

## Сервисы

- GitHub — публичный или приватный репозиторий с кодом.
- HuggingFace Spaces — Docker-хостинг приложения.
- Cloudflare Workers — прокси к Telegram Bot API.
- cron-job.org или другой пингер — опционально, если нужно не давать Space
  засыпать.

## Правила безопасности

Перед любым публичным push:

1. Проверь `.gitignore`: `.env`, базы, кеши, `.DS_Store`, виртуальное окружение
   не должны попадать в Git.
2. Просканируй проект на токены:

```bash
rg -n "[0-9]{6,}:[A-Za-z0-9_-]{20,}|TOKEN\\s*=\\s*['\"][^'\"]+|WEBHOOK_SECRET|BITRIX24_WEBHOOK_URL|TELEGRAM_BOT_TOKEN|MAX_BOT_TOKEN" -g '!*.png'
```

3. Если нашел hardcoded токен в demo/MVP-файлах, замени его на чтение из
   переменной окружения.
4. Не выводи реальные токены в чат. Если надо проверить наличие значения,
   выводи только `set/not set` или длину.

## Шаг 1. Подготовь приложение к Docker Space

В проекте должен быть ASGI entrypoint, например:

```python
# src/mybot/app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Для Telegram webhook нужен endpoint вида:

```text
POST /webhooks/telegram
```

Если проект использует `aiogram`, бот должен поддерживать Cloudflare Worker как
Telegram API base. Пример идеи:

```python
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

def build_bot(token: str, telegram_api_base: str = "") -> Bot:
    if telegram_api_base:
        base = telegram_api_base.replace("/bot{0}/{1}", "").rstrip("/")
        api = TelegramAPIServer.from_base(base)
        return Bot(token=token, session=AiohttpSession(api=api))
    return Bot(token=token)
```

На старте ASGI-приложения зарегистрируй webhook:

```python
await bot.set_webhook(
    f"{WEBHOOK_HOST.rstrip('/')}/webhooks/telegram",
    secret_token=TELEGRAM_WEBHOOK_SECRET or None,
    drop_pending_updates=True,
)
```

Для FastAPI используй lifespan handler вместо устаревшего `on_event`.

## Шаг 2. Создай Dockerfile

Для пакетного Python-проекта с `pyproject.toml`:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 7860

CMD ["uvicorn", "mybot.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

Замени `mybot.app:app` на реальный import path проекта.

Добавь `.dockerignore`:

```gitignore
.DS_Store
.env
.git
.pytest_cache
.ruff_cache
.venv
__pycache__
*.db
*.sqlite3
*.py[cod]
```

Для HuggingFace Space добавь YAML metadata в начало `README.md`:

```markdown
---
title: Project Name
sdk: docker
app_port: 7860
---
```

## Шаг 3. Настрой Cloudflare Worker

Если Worker еще не создан:

1. Зайди на Cloudflare.
2. Workers & Pages → Create → Start with Hello World.
3. Вставь код:

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const telegramUrl = "https://api.telegram.org" + url.pathname + url.search;
    return fetch(new Request(telegramUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    }));
  }
};
```

4. Скопируй Worker URL, например:

```text
https://cold-dew-ccfb.realdredi.workers.dev
```

В проекте используй переменную:

```text
TELEGRAM_API_BASE=https://your-worker.workers.dev
```

Если старый проект ожидает формат `TELEGRAM_API_URL`, допустимо:

```text
TELEGRAM_API_URL=https://your-worker.workers.dev/bot{0}/{1}
```

## Шаг 4. Проверь проект локально

Запусти тесты и линтер:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Если в проекте есть env validator, запусти его:

```bash
.venv/bin/mebelbot validate-env
```

Валидатор может оставлять предупреждения по отложенным интеграциям, но не должен
падать с ошибками для выбранного режима деплоя.

## Шаг 5. Инициализируй Git и сделай первый коммит

Если в проекте еще нет `.git`:

```bash
git init
git branch -m main
```

Добавь правило в README/AGENTS/TASKS, чтобы после каждого изменения пушить в
оба remotes:

```bash
git push origin main
git push huggingface main
```

Затем:

```bash
git add .
git commit -m "Prepare deployment"
```

## Шаг 6. Создай новый GitHub repository

Если установлен `gh` и он авторизован:

```bash
gh repo create OWNER/REPO --public --source=. --remote=origin --push
```

Если `gh` нет, но git credential helper уже хранит GitHub token, можно создать
репозиторий через GitHub REST API:

```bash
cred=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill)
user=$(printf '%s\n' "$cred" | awk -F= '$1=="username"{print $2; exit}')
pass=$(printf '%s\n' "$cred" | awk -F= '$1=="password"{print $2; exit}')

curl -sS \
  -u "$user:$pass" \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  https://api.github.com/user/repos \
  -d '{"name":"REPO","private":false,"description":"Project deployment repository."}'
```

Потом:

```bash
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

Если имя занято, выбери новое понятное имя, например `project-deploy`.

## Шаг 7. Создай HuggingFace Docker Space

Проверь авторизацию:

```bash
hf auth whoami
```

Создай Space:

```bash
hf repo create HF_USER/SPACE_NAME --type space --space-sdk docker --public --exist-ok
```

Пример:

```bash
hf repo create amiasayedau/mebelbot-deploy --type space --space-sdk docker --public --exist-ok
```

Узнай публичный app URL:

```bash
hf spaces info HF_USER/SPACE_NAME
```

В ответе поле `host` будет вида:

```text
https://hf-user-space-name.hf.space
```

Добавь remote:

```bash
git remote add huggingface https://huggingface.co/spaces/HF_USER/SPACE_NAME
```

Если Space создал стартовый README и обычный push отклоняется, сначала получи
remote branch и затем замени стартовый коммит своим проектом:

```bash
git fetch huggingface main
git push --force-with-lease huggingface main
```

Для следующих изменений используй обычный push:

```bash
git push huggingface main
```

## Шаг 8. Добавь HuggingFace secrets и variables

Secrets:

```bash
hf spaces secrets add HF_USER/SPACE_NAME \
  -s TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -s TELEGRAM_WEBHOOK_SECRET="$TELEGRAM_WEBHOOK_SECRET"
```

Variables:

```bash
hf spaces variables add HF_USER/SPACE_NAME \
  -e WEBHOOK_HOST=https://hf-user-space-name.hf.space \
  -e TELEGRAM_API_BASE=https://your-worker.workers.dev \
  -e DATABASE_URL=sqlite:///data/mebelbot.sqlite3
```

Если проекту нужны дополнительные переменные, добавь их так же:

```bash
hf spaces secrets add HF_USER/SPACE_NAME -s SOME_SECRET="$SOME_SECRET"
hf spaces variables add HF_USER/SPACE_NAME -e SOME_PUBLIC_SETTING=value
```

Не добавляй пустые или placeholder-переменные для отключенных интеграций, если
код трактует их как включение интеграции.

## Шаг 9. Пуш в оба remotes

После каждого изменения:

```bash
git status --short
.venv/bin/pytest -q
.venv/bin/ruff check .
git add .
git commit -m "Describe change"
git push origin main
git push huggingface main
```

Если изменений нет, коммит не нужен.

## Шаг 10. Проверь сборку и запуск Space

Смотри статус:

```bash
hf spaces info HF_USER/SPACE_NAME
```

Смотри build logs:

```bash
hf spaces logs HF_USER/SPACE_NAME --build --tail 120
```

Смотри runtime logs:

```bash
hf spaces logs HF_USER/SPACE_NAME --tail 120
```

Проверь health endpoint:

```bash
curl -sS -i https://hf-user-space-name.hf.space/health
```

Успешный ответ:

```text
HTTP/2 200
...
{"status":"ok"}
```

## Шаг 11. Проверь Telegram webhook

Через прямой Telegram API, если доступен:

```bash
python3 - <<'PY'
import json
import os
import urllib.request

token = os.environ["TELEGRAM_BOT_TOKEN"]
url = f"https://api.telegram.org/bot{token}/getWebhookInfo"

with urllib.request.urlopen(url, timeout=20) as response:
    data = json.load(response)

result = data.get("result", {})
print(json.dumps({
    "ok": data.get("ok"),
    "url": result.get("url"),
    "pending_update_count": result.get("pending_update_count"),
    "last_error_message": result.get("last_error_message"),
}, ensure_ascii=False, indent=2))
PY
```

Успешный результат:

```json
{
  "ok": true,
  "url": "https://hf-user-space-name.hf.space/webhooks/telegram",
  "pending_update_count": 0,
  "last_error_message": null
}
```

Если локальная проверка через Cloudflare Worker дает `403` и `error code: 1010`,
это может быть Cloudflare-защита именно для локального клиента. Смотри runtime
logs Space и прямой `getWebhookInfo`: если webhook зарегистрирован и ошибок нет,
деплой считается рабочим.

## Диагностика

### GitHub repository name already exists

Выбери новое имя, например `project-deploy`, и используй его для remote `origin`.

### HuggingFace push rejected: fetch first

Space уже содержит стартовый коммит. Для первого пуша:

```bash
git fetch huggingface main
git push --force-with-lease huggingface main
```

### HuggingFace warning: empty or missing yaml metadata in repo card

Добавь YAML metadata в начало `README.md`:

```markdown
---
title: Project Name
sdk: docker
app_port: 7860
---
```

### Space stage: NO_APP_FILE

Обычно нет `Dockerfile` в корне или README metadata не указывает `sdk: docker`.

### Space stage: BUILD_ERROR

Смотри:

```bash
hf spaces logs HF_USER/SPACE_NAME --build --tail 200
```

Частые причины:

- неверный `CMD` в Dockerfile;
- неправильный import path `module.app:app`;
- пакет не устанавливается через `pip install .`;
- файл, нужный сборке, исключен в `.dockerignore`.

### App starts, но Telegram не отвечает

Проверь:

- `WEBHOOK_HOST` равен публичному `https://...hf.space`;
- endpoint `/webhooks/telegram` существует;
- startup регистрирует webhook;
- `TELEGRAM_BOT_TOKEN` добавлен как secret;
- `TELEGRAM_API_BASE` указывает на Cloudflare Worker без лишнего пути;
- `getWebhookInfo` показывает правильный URL и `last_error_message: null`.

### Space засыпает

На бесплатном тарифе Space может засыпать. Если нужен внешний пинг:

1. Зарегистрируйся на `console.cron-job.org`.
2. Создай cronjob.
3. URL: `https://hf-user-space-name.hf.space/health`.
4. Schedule: каждые 5 минут.

## Реальный пример выполненного деплоя

В проекте `MebelBot` деплой был сделан так:

- GitHub repo: `https://github.com/jxlsij/mebelBot-deploy`
- HuggingFace Space: `https://huggingface.co/spaces/amiasayedau/mebelbot-deploy`
- Public app URL: `https://amiasayedau-mebelbot-deploy.hf.space`
- Cloudflare Worker: `https://cold-dew-ccfb.realdredi.workers.dev`
- Docker runtime: `uvicorn mebelbot.app:app --host 0.0.0.0 --port 7860`
- Health check: `https://amiasayedau-mebelbot-deploy.hf.space/health`

Проверки после деплоя:

```text
pytest: 41 passed
ruff: All checks passed
HuggingFace stage: RUNNING
/health: {"status":"ok"}
Telegram webhook URL: https://amiasayedau-mebelbot-deploy.hf.space/webhooks/telegram
Telegram last_error_message: null
```

После этого в проект записали постоянное правило:

```bash
git push origin main
git push huggingface main
```

То есть каждый production-ready коммит должен уходить и в GitHub, и в
HuggingFace Space.
