from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import qrcode

from mebelbot.config import get_settings
from mebelbot.domain import SOURCE_RE


@dataclass(frozen=True)
class Speaker:
    code: str
    name: str


@dataclass(frozen=True)
class QRArtifact:
    code: str
    name: str
    telegram_link: str
    max_link: str
    telegram_qr: Path
    max_qr: Path


def telegram_link(bot_username: str, source_code: str) -> str:
    username = bot_username.removeprefix("@")
    return f"https://t.me/{username}?start=src_{source_code}"


def max_link(bot_username: str, source_code: str) -> str:
    username = bot_username.removeprefix("@")
    return f"https://max.ru/{username}?start=src_{source_code}"


def save_qr(link: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = qrcode.make(link)
    image.save(path)


def read_speakers(path: Path) -> list[Speaker]:
    speakers: list[Speaker] = []
    seen_codes: set[str] = set()
    with path.open(newline="", encoding="utf-8") as csv_file:
        for line_number, row in enumerate(csv.DictReader(csv_file), start=2):
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            if not code:
                raise ValueError(f"{path}:{line_number}: speaker code is required")
            if not SOURCE_RE.fullmatch(code):
                raise ValueError(
                    f"{path}:{line_number}: speaker code must contain only letters, "
                    "numbers, '_' or '-' and be at most 64 characters"
                )
            if code in seen_codes:
                raise ValueError(f"{path}:{line_number}: duplicate speaker code {code!r}")
            seen_codes.add(code)
            speakers.append(Speaker(code=code, name=name))
    return speakers


def validate_bot_username(username: str, *, field_name: str) -> str:
    normalized = username.strip().removeprefix("@")
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if normalized.startswith("your_") or normalized in {"tg_bot", "max_bot", "telegram_bot"}:
        raise ValueError(f"{field_name} must be a real bot username, got placeholder {username!r}")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{field_name} must not contain whitespace")
    return normalized


def generate_qr_artifacts(
    *,
    speakers: list[Speaker],
    telegram_username: str,
    max_username: str,
    output: Path,
) -> list[QRArtifact]:
    artifacts: list[QRArtifact] = []
    telegram_username = validate_bot_username(
        telegram_username,
        field_name="telegram_username",
    )
    max_username = validate_bot_username(max_username, field_name="max_username")
    for speaker in speakers:
        tg = telegram_link(telegram_username, speaker.code)
        mx = max_link(max_username, speaker.code)
        telegram_qr = output / f"{speaker.code}-telegram.png"
        max_qr = output / f"{speaker.code}-max.png"
        save_qr(tg, telegram_qr)
        save_qr(mx, max_qr)
        artifacts.append(
            QRArtifact(
                code=speaker.code,
                name=speaker.name,
                telegram_link=tg,
                max_link=mx,
                telegram_qr=telegram_qr,
                max_qr=max_qr,
            )
        )
    return artifacts


def write_manifest(artifacts: list[QRArtifact], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "code",
                "name",
                "telegram_link",
                "max_link",
                "telegram_qr",
                "max_qr",
            ],
        )
        writer.writeheader()
        for artifact in artifacts:
            writer.writerow(
                {
                    "code": artifact.code,
                    "name": artifact.name,
                    "telegram_link": artifact.telegram_link,
                    "max_link": artifact.max_link,
                    "telegram_qr": str(artifact.telegram_qr),
                    "max_qr": str(artifact.max_qr),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate speaker deep links and QR codes")
    parser.add_argument("--speakers", required=True, help="CSV with columns code,name")
    parser.add_argument(
        "--telegram-username",
        default=None,
        help="Telegram bot username. Defaults to TELEGRAM_BOT_USERNAME from .env.",
    )
    parser.add_argument(
        "--max-username",
        default=None,
        help="Max bot username. Defaults to MAX_BOT_USERNAME from .env.",
    )
    parser.add_argument("--out", default="data/qr")
    parser.add_argument(
        "--manifest",
        default=None,
        help="CSV manifest with generated links and PNG paths. Defaults to <out>/manifest.csv.",
    )
    args = parser.parse_args()

    settings = get_settings()
    telegram_username = args.telegram_username or settings.telegram_bot_username
    max_username = args.max_username or settings.max_bot_username
    output = Path(args.out)
    manifest = Path(args.manifest) if args.manifest else output / "manifest.csv"
    try:
        artifacts = generate_qr_artifacts(
            speakers=read_speakers(Path(args.speakers)),
            telegram_username=telegram_username,
            max_username=max_username,
            output=output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    write_manifest(artifacts, manifest)
    for artifact in artifacts:
        print(f"{artifact.code}: telegram={artifact.telegram_link} max={artifact.max_link}")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
