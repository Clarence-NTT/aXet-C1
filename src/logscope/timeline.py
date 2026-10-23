"""Timeline command logic."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import TextIO

from logscope.parser import parse_line

_BUCKET_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smh])$")
_LEVELS = {"INFO", "WARN", "ERROR"}


@dataclass(frozen=True, slots=True)
class TimelineBucket:
    """One bucket in a timeline result."""

    start: datetime
    count: int


@dataclass(frozen=True, slots=True)
class TimelineResult:
    """Timeline output data."""

    lines: dict[str, int]
    bucket: str
    level: str
    buckets: list[TimelineBucket]


class BucketValueError(ValueError):
    """Raised when a bucket argument is invalid."""


def parse_bucket(bucket: str) -> timedelta:
    """Parse a bucket string into a duration."""
    match = _BUCKET_PATTERN.match(bucket)
    if match is None:
        raise BucketValueError(f"invalid bucket: {bucket}")

    value = int(match.group("value"))
    unit = match.group("unit")
    seconds = value
    if unit == "m":
        seconds *= 60
    elif unit == "h":
        seconds *= 3600

    if seconds < 1:
        raise BucketValueError(f"invalid bucket: {bucket}")

    return timedelta(seconds=seconds)


def align_timestamp(timestamp: datetime, bucket_size: timedelta) -> datetime:
    """Align a timestamp down to its bucket boundary."""
    seconds = int(bucket_size.total_seconds())
    day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    offset = int((timestamp - day_start).total_seconds())
    aligned_offset = (offset // seconds) * seconds
    return day_start + timedelta(seconds=aligned_offset)


def build_bar(count: int, max_count: int, width: int = 50) -> str:
    """Return a scaled text bar for one bucket."""
    if count <= 0 or max_count <= 0:
        return ""

    scaled = max(1, round((count / max_count) * width))
    return "█" * scaled


def timeline_stream(handle: TextIO, bucket: str = "15m", level: str = "ERROR") -> TimelineResult:
    """Build a timeline from an open text stream."""
    if level not in _LEVELS:
        raise BucketValueError(f"invalid level: {level}")

    bucket_size = parse_bucket(bucket)
    total_lines = 0
    valid_lines = 0
    malformed_lines = 0
    blank_lines = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    bucket_counts: Counter[datetime] = Counter()

    for line in handle:
        total_lines += 1
        outcome = parse_line(line)
        if outcome.is_blank:
            blank_lines += 1
            continue
        if outcome.is_malformed or outcome.entry is None:
            malformed_lines += 1
            continue

        entry = outcome.entry
        valid_lines += 1
        if first_timestamp is None or entry.timestamp < first_timestamp:
            first_timestamp = entry.timestamp
        if last_timestamp is None or entry.timestamp > last_timestamp:
            last_timestamp = entry.timestamp
        if entry.level == level:
            bucket_counts[align_timestamp(entry.timestamp, bucket_size)] += 1

    buckets: list[TimelineBucket] = []
    if first_timestamp is not None and last_timestamp is not None:
        start = align_timestamp(first_timestamp, bucket_size)
        end = align_timestamp(last_timestamp, bucket_size)
        current = start
        while current <= end:
            buckets.append(TimelineBucket(start=current, count=bucket_counts.get(current, 0)))
            current += bucket_size

    return TimelineResult(
        lines={
            "total": total_lines,
            "valid": valid_lines,
            "malformed": malformed_lines,
            "blank": blank_lines,
        },
        bucket=bucket,
        level=level,
        buckets=buckets,
    )


def timeline_file(path: str | Path, bucket: str = "15m", level: str = "ERROR") -> TimelineResult:
    """Build a timeline from a file path."""
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        return timeline_stream(handle, bucket=bucket, level=level)
