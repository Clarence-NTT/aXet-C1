"""Output formatting helpers."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Callable, Iterable

from logscope.grep import GrepResult
from logscope.summary import SummaryResult
from logscope.timeline import TimelineResult, build_bar

Clock = Callable[[], datetime]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def format_summary_text(result: SummaryResult) -> str:
    """Render a summary result as text."""
    lines = [
        "Summary",
        f"lines total={result.lines['total']} valid={result.lines['valid']} malformed={result.lines['malformed']} blank={result.lines['blank']}",
        f"levels INFO={result.levels['INFO']} WARN={result.levels['WARN']} ERROR={result.levels['ERROR']}",
        f"time_range first={_iso(result.first_timestamp) or '-'} last={_iso(result.last_timestamp) or '-'}",
        "top_errors:",
    ]
    if not result.top_errors:
        lines.append("  - none")
    else:
        for item in result.top_errors:
            services = ",".join(item.services)
            lines.append(
                f"  - {item.message} | count={item.count} | services={services} | example={item.example}"
            )
    return "\n".join(lines)


def format_summary_json(result: SummaryResult, file_name: str) -> str:
    """Render a summary result as JSON."""
    payload = {
        "command": "summary",
        "file": file_name,
        "lines": result.lines,
        "levels": result.levels,
        "first_timestamp": _iso(result.first_timestamp),
        "last_timestamp": _iso(result.last_timestamp),
        "top_errors": [asdict(item) for item in result.top_errors],
    }
    return json.dumps(payload, indent=2)


def format_timeline_text(result: TimelineResult) -> str:
    """Render a timeline result as text."""
    max_count = max((bucket.count for bucket in result.buckets), default=0)
    lines = [
        f"Timeline level={result.level} bucket={result.bucket}",
        f"lines total={result.lines['total']} valid={result.lines['valid']} malformed={result.lines['malformed']} blank={result.lines['blank']}",
    ]
    for bucket in result.buckets:
        bar = build_bar(bucket.count, max_count)
        lines.append(f"{bucket.start.strftime('%Y-%m-%d %H:%M')}  {bar:<50}  {bucket.count}")
    return "\n".join(lines)


def format_timeline_json(result: TimelineResult, file_name: str) -> str:
    """Render a timeline result as JSON."""
    payload = {
        "command": "timeline",
        "file": file_name,
        "lines": result.lines,
        "bucket": result.bucket,
        "level": result.level,
        "buckets": [
            {"start": bucket.start.isoformat(), "count": bucket.count}
            for bucket in result.buckets
        ],
    }
    return json.dumps(payload, indent=2)


def format_grep_text(result: GrepResult) -> tuple[str, str]:
    """Render grep output and stderr footer for text mode."""
    stdout = "\n".join(entry.raw_line for entry in result.entries)
    stderr = f"matched={result.matched} malformed={result.lines['malformed']}"
    return stdout, stderr


def format_grep_json(result: GrepResult, file_name: str) -> str:
    """Render grep output as JSON."""
    payload = {
        "command": "grep",
        "file": file_name,
        "lines": result.lines,
        "filters": result.filters,
        "matched": result.matched,
        "entries": [
            {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level,
                "service": entry.service,
                "message": entry.message,
            }
            for entry in result.entries
        ],
    }
    return json.dumps(payload, indent=2)


def _markdown_header(command: str, file_name: str, generated_at: datetime, lines: dict[str, int]) -> list[str]:
    return [
        f"# LogScope {command} report",
        "",
        f"- File: `{file_name}`",
        f"- Generated at: `{generated_at.isoformat()}`",
        f"- Line counts: total={lines['total']}, valid={lines['valid']}, malformed={lines['malformed']}, blank={lines['blank']}",
        "",
    ]


def write_summary_markdown(result: SummaryResult, file_name: str, out_path: str | Path, clock: Clock) -> Path:
    """Write a summary markdown report."""
    output = Path(out_path)
    lines = _markdown_header("summary", file_name, clock(), result.lines)
    lines.extend(
        [
            "## Levels",
            "",
            "| INFO | WARN | ERROR |",
            "|---|---|---|",
            f"| {result.levels['INFO']} | {result.levels['WARN']} | {result.levels['ERROR']} |",
            "",
            "## Time range",
            "",
            f"- First: `{_iso(result.first_timestamp) or '-'}`",
            f"- Last: `{_iso(result.last_timestamp) or '-'}`",
            "",
            "## Top errors",
            "",
            "| Message | Count | Services | Example |",
            "|---|---:|---|---|",
        ]
    )
    for item in result.top_errors:
        lines.append(
            f"| {item.message} | {item.count} | {', '.join(item.services)} | {item.example} |"
        )
    if not result.top_errors:
        lines.append("| none | 0 |  |  |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def write_timeline_markdown(result: TimelineResult, file_name: str, out_path: str | Path, clock: Clock) -> Path:
    """Write a timeline markdown report."""
    output = Path(out_path)
    lines = _markdown_header("timeline", file_name, clock(), result.lines)
    lines.extend(["## Chart", "", "```text", format_timeline_text(result), "```", ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def write_grep_markdown(result: GrepResult, file_name: str, out_path: str | Path, clock: Clock) -> Path:
    """Write a grep markdown report."""
    output = Path(out_path)
    lines = _markdown_header("grep", file_name, clock(), result.lines)
    lines.extend(["## Matched lines", "", "```text"])
    lines.extend(entry.raw_line for entry in result.entries)
    lines.extend(["```", ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def default_report_path(command: str, clock: Clock) -> Path:
    """Return the default markdown report path."""
    return Path(f"logscope-{command}-{clock().strftime('%Y%m%d-%H%M%S')}.md")
