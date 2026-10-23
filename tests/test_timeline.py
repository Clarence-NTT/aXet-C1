from io import StringIO

import pytest

from logscope.timeline import (
    BucketValueError,
    align_timestamp,
    build_bar,
    parse_bucket,
    timeline_stream,
)


def test_parse_bucket_accepts_seconds_minutes_and_hours() -> None:
    assert parse_bucket("30s").total_seconds() == 30
    assert parse_bucket("15m").total_seconds() == 900
    assert parse_bucket("1h").total_seconds() == 3600


@pytest.mark.parametrize("bucket", ["0s", "15", "ms", "-1m", "1d"])
def test_parse_bucket_rejects_invalid_values(bucket: str) -> None:
    with pytest.raises(BucketValueError):
        parse_bucket(bucket)


def test_align_timestamp_to_bucket_boundary() -> None:
    result = align_timestamp(
        timeline_stream(StringIO("2026-10-01 09:16:45 ERROR [svc] boom\n"), bucket="15m").buckets[0].start,
        parse_bucket("15m"),
    )

    assert result.isoformat(sep=" ") == "2026-10-01 09:15:00"


def test_timeline_includes_empty_buckets_and_counts_errors() -> None:
    handle = StringIO(
        "\n".join(
            [
                "2026-10-01 09:18:00 ERROR [svc] failed",
                "2026-10-01 09:02:00 INFO [svc] start",
                "bad line",
                "2026-10-01 09:31:00 ERROR [svc] failed again",
            ]
        )
    )

    result = timeline_stream(handle, bucket="15m")

    assert result.lines == {"total": 4, "valid": 3, "malformed": 1, "blank": 0}
    assert [bucket.start.isoformat(sep=" ") for bucket in result.buckets] == [
        "2026-10-01 09:00:00",
        "2026-10-01 09:15:00",
        "2026-10-01 09:30:00",
    ]
    assert [bucket.count for bucket in result.buckets] == [0, 1, 1]


def test_timeline_supports_alternate_levels() -> None:
    handle = StringIO(
        "\n".join(
            [
                "2026-10-01 09:00:00 INFO [svc] hello",
                "2026-10-01 09:01:00 WARN [svc] caution",
                "2026-10-01 09:02:00 WARN [svc] caution again",
            ]
        )
    )

    result = timeline_stream(handle, bucket="1m", level="WARN")

    assert [bucket.count for bucket in result.buckets] == [0, 1, 1]


def test_timeline_handles_all_malformed_input() -> None:
    result = timeline_stream(StringIO("bad\n\nDEBUG nope\n"))

    assert result.lines == {"total": 3, "valid": 0, "malformed": 2, "blank": 1}
    assert result.buckets == []


def test_build_bar_scales_and_preserves_non_zero_visibility() -> None:
    assert build_bar(0, 5) == ""
    assert build_bar(1, 100) == "█"
    assert len(build_bar(50, 50)) == 50


def test_timeline_rejects_invalid_level() -> None:
    with pytest.raises(BucketValueError):
        timeline_stream(StringIO("2026-10-01 09:00:00 INFO [svc] ok\n"), level="DEBUG")
