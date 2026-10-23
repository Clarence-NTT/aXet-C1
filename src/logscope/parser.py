"""Log line parsing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?) "
    r"(?P<level>INFO|WARN|WARNING|ERROR) "
    r"\[(?P<service>[^\]]+)\] ?(?P<message>.*)$"
)

LogLevel = Literal["INFO", "WARN", "ERROR"]


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A parsed log entry."""

    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    raw_line: str


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """Result of attempting to parse one log line."""

    entry: LogEntry | None
    is_blank: bool
    is_malformed: bool


def parse_line(line: str) -> ParseOutcome:
    """Parse one log line into a structured outcome."""
    raw_line = line.rstrip("\n\r")
    if raw_line.strip() == "":
        return ParseOutcome(entry=None, is_blank=True, is_malformed=False)

    match = LOG_PATTERN.match(raw_line)
    if match is None:
        return ParseOutcome(entry=None, is_blank=False, is_malformed=True)

    try:
        timestamp = datetime.fromisoformat(match.group("timestamp"))
    except ValueError:
        return ParseOutcome(entry=None, is_blank=False, is_malformed=True)

    level = match.group("level")
    if level == "WARNING":
        level = "WARN"

    entry = LogEntry(
        timestamp=timestamp,
        level=level,
        service=match.group("service"),
        message=match.group("message"),
        raw_line=raw_line,
    )
    return ParseOutcome(entry=entry, is_blank=False, is_malformed=False)
