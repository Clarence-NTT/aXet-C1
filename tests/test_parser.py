from datetime import datetime

from logscope.parser import parse_line


def test_parse_valid_line_with_fractional_seconds() -> None:
    outcome = parse_line(
        "2026-10-01 09:00:12.345 ERROR [payment-api] Timeout calling bank gateway"
    )

    assert outcome.is_blank is False
    assert outcome.is_malformed is False
    assert outcome.entry is not None
    assert outcome.entry.timestamp == datetime(2026, 10, 1, 9, 0, 12, 345000)
    assert outcome.entry.level == "ERROR"
    assert outcome.entry.service == "payment-api"
    assert outcome.entry.message == "Timeout calling bank gateway"


def test_parse_warning_is_normalised_to_warn() -> None:
    outcome = parse_line("2026-10-01 09:00:12 WARNING [auth] Password expires soon")

    assert outcome.entry is not None
    assert outcome.entry.level == "WARN"


def test_parse_blank_line() -> None:
    outcome = parse_line("   \n")

    assert outcome.entry is None
    assert outcome.is_blank is True
    assert outcome.is_malformed is False


def test_parse_invalid_shape_is_malformed() -> None:
    outcome = parse_line("not a log line")

    assert outcome.entry is None
    assert outcome.is_blank is False
    assert outcome.is_malformed is True


def test_parse_invalid_level_is_malformed() -> None:
    outcome = parse_line("2026-10-01 09:00:12 DEBUG [auth] hidden message")

    assert outcome.entry is None
    assert outcome.is_malformed is True


def test_parse_invalid_date_is_malformed() -> None:
    outcome = parse_line("2026-02-30 09:00:12 INFO [auth] impossible day")

    assert outcome.entry is None
    assert outcome.is_malformed is True


def test_parse_empty_message_is_allowed() -> None:
    outcome = parse_line("2026-10-01 09:00:12 INFO [auth] ")

    assert outcome.entry is not None
    assert outcome.entry.message == ""


def test_parse_invalid_bytes_after_utf8_replace_do_not_crash() -> None:
    decoded = b"2026-10-01 09:00:12 INFO [api] bad\xfftext\n".decode(
        "utf-8", errors="replace"
    )

    outcome = parse_line(decoded)

    assert outcome.entry is not None
    assert outcome.entry.message == "bad�text"
