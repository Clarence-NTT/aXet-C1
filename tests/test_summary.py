from io import StringIO
from unittest.mock import patch

from logscope.summary import MAX_DISTINCT_ERRORS, OTHER_KEY, summarise_stream


def test_summary_counts_levels_and_time_range() -> None:
    handle = StringIO(
        "\n".join(
            [
                "2026-10-01 09:15:00 ERROR [payments] Timeout calling bank gateway after 3000 ms",
                "2026-10-01 09:00:00 INFO [api] Request received",
                "bad line",
                "   ",
                "2026-10-01 09:05:00 WARNING [worker] Queue depth rising",
                "2026-10-01 09:20:00 ERROR [payments] Timeout calling bank gateway after 1500 ms",
            ]
        )
    )

    result = summarise_stream(handle)

    assert result.lines == {"total": 6, "valid": 4, "malformed": 1, "blank": 1}
    assert result.levels == {"INFO": 1, "WARN": 1, "ERROR": 2}
    assert result.first_timestamp.isoformat(sep=" ") == "2026-10-01 09:00:00"
    assert result.last_timestamp.isoformat(sep=" ") == "2026-10-01 09:20:00"


def test_summary_groups_errors_and_sorts_services() -> None:
    handle = StringIO(
        "\n".join(
            [
                "2026-10-01 09:00:00 ERROR [billing] Failure for order 100",
                "2026-10-01 09:01:00 ERROR [checkout] Failure for order 200",
                "2026-10-01 09:02:00 ERROR [billing] Another issue 9",
                "2026-10-01 09:03:00 ERROR [api] Another issue 8",
                "2026-10-01 09:04:00 ERROR [api] Another issue 7",
            ]
        )
    )

    result = summarise_stream(handle)

    assert [error.message for error in result.top_errors] == [
        "Another issue <n>",
        "Failure for order <n>",
    ]
    assert result.top_errors[0].count == 3
    assert result.top_errors[0].services == ["api", "billing"]
    assert result.top_errors[0].example == "Another issue 9"
    assert result.top_errors[1].services == ["billing", "checkout"]


def test_summary_breaks_ties_alphabetically() -> None:
    handle = StringIO(
        "\n".join(
            [
                "2026-10-01 09:00:00 ERROR [svc] Zebra 1",
                "2026-10-01 09:01:00 ERROR [svc] Alpha 1",
            ]
        )
    )

    result = summarise_stream(handle)

    assert [error.message for error in result.top_errors] == ["Alpha <n>", "Zebra <n>"]


def test_summary_caps_distinct_error_messages() -> None:
    unique_lines = [
        f"2026-10-01 09:00:00 ERROR [svc] unique message code:{index}"
        for index in range(MAX_DISTINCT_ERRORS)
    ]
    overflow_lines = [
        f"2026-10-01 09:10:{second:02d} ERROR [overflow] repeated overflow {second}"
        for second in range(6)
    ]

    with patch("logscope.summary.normalise_message", side_effect=unique_lines + ["repeated-overflow"] * 6):
        result = summarise_stream(StringIO("\n".join(unique_lines + overflow_lines)))

    overflow = next(error for error in result.top_errors if error.message == OTHER_KEY)
    assert overflow.count == 6
    assert overflow.services == ["overflow"]
    assert overflow.example == "repeated overflow 0"


def test_summary_always_reports_zero_levels() -> None:
    result = summarise_stream(StringIO("2026-10-01 09:00:00 INFO [svc] ok\n"))

    assert result.levels == {"INFO": 1, "WARN": 0, "ERROR": 0}
    assert result.top_errors == []
