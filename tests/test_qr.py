from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mebelbot.qr import (
    Speaker,
    generate_qr_artifacts,
    max_link,
    qr_png_bytes,
    read_speakers,
    save_qr,
    telegram_link,
    write_manifest,
)


def test_deep_links_strip_at_prefix() -> None:
    assert telegram_link("@tg_bot", "speaker_1") == "https://t.me/tg_bot?start=src_speaker_1"
    assert max_link("@max_bot", "speaker_1") == "https://max.ru/max_bot?start=src_speaker_1"


def test_save_qr_writes_png(tmp_path) -> None:
    path = tmp_path / "speaker_1-telegram.png"

    save_qr("https://t.me/tg_bot?start=src_speaker_1", path)

    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_qr_png_bytes_returns_png() -> None:
    content = qr_png_bytes("https://t.me/tg_bot?start=src_speaker_1")

    assert content.startswith(b"\x89PNG\r\n\x1a\n")


def test_read_speakers_rejects_duplicate_codes(tmp_path) -> None:
    path = tmp_path / "speakers.csv"
    path.write_text("code,name\nspeaker_1,One\nspeaker_1,Duplicate\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate speaker code"):
        read_speakers(path)


def test_read_speakers_rejects_invalid_codes(tmp_path) -> None:
    path = tmp_path / "speakers.csv"
    path.write_text("code,name\nspeaker one,Speaker One\n", encoding="utf-8")

    with pytest.raises(ValueError, match="speaker code must contain only"):
        read_speakers(path)


def test_production_speaker_template_is_valid() -> None:
    speakers = read_speakers(Path("data/speakers.production.template.csv"))

    assert [speaker.code for speaker in speakers] == ["speaker_code_1", "speaker_code_2"]


def test_generate_qr_artifacts_rejects_placeholder_usernames(tmp_path) -> None:
    with pytest.raises(ValueError, match="real bot username"):
        generate_qr_artifacts(
            speakers=[Speaker(code="speaker_1", name="Speaker One")],
            telegram_username="your_tg_bot",
            max_username="real_max_bot",
            output=tmp_path / "qr",
        )


def test_generate_qr_artifacts_writes_manifest(tmp_path) -> None:
    artifacts = generate_qr_artifacts(
        speakers=[Speaker(code="speaker_1", name="Speaker One")],
        telegram_username="@real_tg_bot",
        max_username="@real_max_bot",
        output=tmp_path / "qr",
    )
    manifest = tmp_path / "qr" / "manifest.csv"

    write_manifest(artifacts, manifest)

    rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
    assert rows == [
        {
            "code": "speaker_1",
            "name": "Speaker One",
            "telegram_link": "https://t.me/real_tg_bot?start=src_speaker_1",
            "max_link": "https://max.ru/real_max_bot?start=src_speaker_1",
            "telegram_qr": str(tmp_path / "qr" / "speaker_1-telegram.png"),
            "max_qr": str(tmp_path / "qr" / "speaker_1-max.png"),
        }
    ]
    assert (tmp_path / "qr" / "speaker_1-telegram.png").exists()
    assert (tmp_path / "qr" / "speaker_1-max.png").exists()
