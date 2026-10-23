"""Summary command logic."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

from logscope.normalise import normalise_message
from logscope.parser import LogEntry, parse_line

MAX_DISTINCT_ERRORS = 10_000
OTHER_KEY = "<other>"
LEVELS = ("INFO", "WARN", "ERROR")


@dataclass(slots=True)
class ErrorGroup:
    """Aggregated data for one normalised error message."""

    count: int = 0
    services: set[str] = field(default_factory=set)
    example: str = ""


@dataclass(frozen=True, slots=True)
class TopError:
    """One top error row."""

    message: str
    count: int
    services: list[str]
    example: str


@dataclass(frozen=True, slots=True)
class SummaryResult:
    """Summary output data."""

    lines: dict[str, int]
    levels: dict[str, int]
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    top_errors: list[TopError]


@dataclass(slots=True)
class SummaryAccumulator:
    """Mutable streaming summary state."""

    total_lines: int = 0
    valid_lines: int = 0
    malformed_lines: int = 0
    blank_lines: int = 0
    level_counts: Counter[str] = field(default_factory=Counter)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    error_groups: dict[str, ErrorGroup] = field(default_factory=dict)
    overflow_error_count: int = 0
    overflow_example: str = ""
    overflow_services: set[str] = field(default_factory=set)

    def consume_line(self, line: str) -> None:
        """Update state from one raw line."""
        self.total_lines += 1
        outcome = parse_line(line)
        if outcome.is_blank:
            self.blank_lines += 1
            return
        if outcome.is_malformed or outcome.entry is None:
            self.malformed_lines += 1
            return

        self._consume_entry(outcome.entry)

    def _consume_entry(self, entry: LogEntry) -> None:
        self.valid_lines += 1
        self.level_counts[entry.level] += 1
        if self.first_timestamp is None or entry.timestamp < self.first_timestamp:
            self.first_timestamp = entry.timestamp
        if self.last_timestamp is None or entry.timestamp > self.last_timestamp:
            self.last_timestamp = entry.timestamp

        if entry.level == "ERROR":
            self._consume_error(entry)

    def _consume_error(self, entry: LogEntry) -> None:
        message_key = normalise_message(entry.message)
        group = self.error_groups.get(message_key)
        if group is not None:
            group.count += 1
            group.services.add(entry.service)
            return

        if len(self.error_groups) >= MAX_DISTINCT_ERRORS:
            self.overflow_error_count += 1
            self.overflow_services.add(entry.service)
            if not self.overflow_example:
                self.overflow_example = entry.message
            return

        self.error_groups[message_key] = ErrorGroup(
            count=1,
            services={entry.service},
            example=entry.message,
        )

    def build(self) -> SummaryResult:
        """Return the immutable summary result."""
        top_errors = [
            TopError(
                message=message,
                count=group.count,
                services=sorted(group.services),
                example=group.example,
            )
            for message, group in self.error_groups.items()
        ]
        if self.overflow_error_count:
            top_errors.append(
                TopError(
                    message=OTHER_KEY,
                    count=self.overflow_error_count,
                    services=sorted(self.overflow_services),
                    example=self.overflow_example,
                )
            )

        top_errors.sort(key=lambda item: (-item.count, item.message))

        return SummaryResult(
            lines={
                "total": self.total_lines,
                "valid": self.valid_lines,
                "malformed": self.malformed_lines,
                "blank": self.blank_lines,
            },
            levels={level: self.level_counts.get(level, 0) for level in LEVELS},
            first_timestamp=self.first_timestamp,
            last_timestamp=self.last_timestamp,
            top_errors=top_errors[:5],
        )


def summarise_file(path: str | Path) -> SummaryResult:
    """Summarise a log file."""
    accumulator = SummaryAccumulator()
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        return summarise_stream(handle, accumulator)


def summarise_stream(
    handle: TextIO, accumulator: SummaryAccumulator | None = None
) -> SummaryResult:
    """Summarise an open text stream."""
    active_accumulator = accumulator or SummaryAccumulator()
    for line in handle:
        active_accumulator.consume_line(line)
    return active_accumulator.build()
