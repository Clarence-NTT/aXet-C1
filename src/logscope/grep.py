"""Grep command logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, TextIO

from logscope.parser import LogEntry, parse_line


class FilterValueError(ValueError):
    """Raised when a grep filter argument is invalid."""


@dataclass(frozen=True, slots=True)
class GrepFilters:
    """Filter options for grep."""

    levels: frozenset[str] = frozenset()
    since: datetime | None = None
    until: datetime | None = None
    service: str | None = None
    contains: str | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class GrepEntry:
    """One grep result entry."""

    timestamp: datetime
    level: str
    service: str
    message: str
    raw_line: str


@dataclass(frozen=True, slots=True)
class GrepResult:
    """Streaming grep output data."""

    lines: dict[str, int]
    filters: dict[str, object]
    matched: int
    entries: tuple[GrepEntry, ...]


def parse_filter_datetime(value: str) -> datetime:
    """Parse a grep datetime filter."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise FilterValueError(f"invalid datetime: {value}")


def _matches(entry: LogEntry, filters: GrepFilters) -> bool:
    if filters.levels and entry.level not in filters.levels:
        return False
    if filters.since is not None and entry.timestamp < filters.since:
        return False
    if filters.until is not None and entry.timestamp >= filters.until:
        return False
    if filters.service is not None and entry.service != filters.service:
        return False
    if filters.contains is not None and filters.contains not in entry.message:
        return False
    return True


def grep_stream(handle: TextIO, filters: GrepFilters | None = None) -> GrepResult:
    """Collect grep results from an open text stream."""
    active_filters = filters or GrepFilters()
    if active_filters.limit is not None and active_filters.limit < 0:
        raise FilterValueError("limit must be non-negative")

    total_lines = 0
    valid_lines = 0
    malformed_lines = 0
    blank_lines = 0
    matched = 0
    entries: list[GrepEntry] = []

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
        if not _matches(entry, active_filters):
            continue

        entries.append(
            GrepEntry(
                timestamp=entry.timestamp,
                level=entry.level,
                service=entry.service,
                message=entry.message,
                raw_line=entry.raw_line,
            )
        )
        matched += 1
        if active_filters.limit is not None and matched >= active_filters.limit:
            break

    return GrepResult(
        lines={
            "total": total_lines,
            "valid": valid_lines,
            "malformed": malformed_lines,
            "blank": blank_lines,
        },
        filters={
            "levels": sorted(active_filters.levels),
            "since": active_filters.since.isoformat() if active_filters.since else None,
            "until": active_filters.until.isoformat() if active_filters.until else None,
            "service": active_filters.service,
            "contains": active_filters.contains,
            "limit": active_filters.limit,
        },
        matched=matched,
        entries=tuple(entries),
    )


def grep_file(path: str | Path, filters: GrepFilters | None = None) -> GrepResult:
    """Collect grep results from a file path."""
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        return grep_stream(handle, filters=filters)


def iter_raw_lines(result: GrepResult) -> Iterator[str]:
    """Yield raw lines from a grep result."""
    for entry in result.entries:
        yield entry.raw_line


def build_filters(
    *,
    levels: Iterable[str] | None = None,
    since: str | None = None,
    until: str | None = None,
    service: str | None = None,
    contains: str | None = None,
    limit: int | None = None,
) -> GrepFilters:
    """Construct validated grep filters from CLI-style values."""
    selected_levels = frozenset(levels or [])
    invalid_levels = sorted(level for level in selected_levels if level not in {"INFO", "WARN", "ERROR"})
    if invalid_levels:
        raise FilterValueError(f"invalid level: {invalid_levels[0]}")

    return GrepFilters(
        levels=selected_levels,
        since=parse_filter_datetime(since) if since else None,
        until=parse_filter_datetime(until) if until else None,
        service=service,
        contains=contains,
        limit=limit,
    )
