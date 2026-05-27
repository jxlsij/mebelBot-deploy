from mebelbot.domain import parse_start_payload


def test_parse_start_payload_accepts_telegram_source() -> None:
    assert parse_start_payload("/start src_speaker-01") == "speaker-01"


def test_parse_start_payload_rejects_unsafe_value() -> None:
    assert parse_start_payload("/start ../../secret") is None
