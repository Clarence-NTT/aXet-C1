from io import StringIO

import pytest

from logscope.grep import build_filters, grep_stream, parse_filter_datetime, FilterValueError


def test_parse_filter_datetime_supports_minutes_and_seconds() -> None:
    assert parse_filter_datetime("2026-10-01 09:00").isoformat(sep=" ") == "2026-10-01 09:00:00"
    assert parse_filter_datetime("2026-10-01 09:00:05").isoformat(sep=" ") == "2026-10-01 09:00:05"


@pytest.mark.parametrize("value", ["2026/10/01 09:00", "2026-10-01", "bad"])
def test_parse_filter_datetime_rejects_invalid_values(value: str) -> None:
    with pytest.raises(FilterValueError):
        parse_filter_datetime(value)


def test_grep_without_filters_returns_all_valid_lines() -> None:
    result = grep_stream(
        StringIO(
            "\n".join(
                [
                    "2026-10-01 09:00:00 INFO [api] hello",
                    "bad line",
                    "2026-10-01 09:01:00 ERROR [api] boom",
                ]
            )
        )
    )

    assert result.lines == {"total": 3, "valid": 2, "malformed": 1, "blank": 0}
    assert result.matched == 2
    assert [entry.raw_line for entry in result.entries] == [
        "2026-10-01 09:00:00 INFO [api] hello",
        "2026-10-01 09:01:00 ERROR [api] boom",
    ]


def test_grep_applies_combined_filters_in_file_order() -> None:
    filters = build_filters(levels=["ERROR"], since="2026-10-01 09:00", service="api", contains="bank")
    result = grep_stream(
        StringIO(
            "\n".join(
                [
                    "2026-10-01 08:59:00 ERROR [api] bank timeout",
                    "2026-10-01 09:00:00 ERROR [api] bank timeout",
                    "2026-10-01 09:01:00 ERROR [worker] bank timeout",
                    "2026-10-01 09:02:00 ERROR [api] cache miss",
                    "2026-10-01 09:03:00 ERROR [api] bank timeout 2",
                ]
            )
        ),
        filters=filters,
    )

    assert [entry.raw_line for entry in result.entries] == [
        "2026-10-01 09:00:00 ERROR [api] bank timeout",
        "2026-10-01 09:03:00 ERROR [api] bank timeout 2",
    ]


def test_grep_honours_until_and_limit_with_partial_counts() -> None:
    filters = build_filters(until="2026-10-01 09:02", limit=1)
    result = grep_stream(
        StringIO(
            "\n".join(
                [
                    "2026-10-01 09:00:00 INFO [api] first",
                    "bad line",
                    "2026-10-01 09:01:00 INFO [api] second",
                    "2026-10-01 09:03:00 INFO [api] third",
                ]
            )
        ),
        filters=filters,
    )

    assert result.matched == 1
    assert result.lines == {"total": 1, "valid": 1, "malformed": 0, "blank": 0}
    assert result.entries[0].raw_line == "2026-10-01 09:00:00 INFO [api] first"


def test_grep_reports_zero_matches() -> None:
    filters = build_filters(levels=["WARN"])
    result = grep_stream(StringIO("2026-10-01 09:00:00 INFO [api] ok\n"), filters=filters)

    assert result.matched == 0
    assert result.entries == ()
    assert result.lines == {"total": 1, "valid": 1, "malformed": 0, "blank": 0}


def test_grep_handles_all_malformed_input() -> None:
    result = grep_stream(StringIO("bad\n\nDEBUG nope\n"))

    assert result.matched == 0
    assert result.lines == {"total": 3, "valid": 0, "malformed": 2, "blank": 1}


def test_build_filters_rejects_invalid_level_and_limit() -> None:
    with pytest.raises(FilterValueError):
        build_filters(levels=["DEBUG"])

    with pytest.raises(FilterValueError):
        grep_stream(StringIO("2026-10-01 09:00:00 INFO [api] ok\n"), build_filters(limit=-1))
