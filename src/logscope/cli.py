"""CLI entry point."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from logscope.formatters import (
    default_report_path,
    format_grep_json,
    format_grep_text,
    format_summary_json,
    format_summary_text,
    format_timeline_json,
    format_timeline_text,
    write_grep_markdown,
    write_summary_markdown,
    write_timeline_markdown,
)
from logscope.grep import FilterValueError, build_filters, grep_file
from logscope.summary import summarise_file
from logscope.timeline import BucketValueError, timeline_file


class CliRuntimeError(RuntimeError):
    """Raised for expected runtime failures."""


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(prog="logscope")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary")
    _add_common_options(summary_parser)

    timeline_parser = subparsers.add_parser("timeline")
    _add_common_options(timeline_parser)
    timeline_parser.add_argument("--bucket", default="15m")
    timeline_parser.add_argument("--level", default="ERROR")

    grep_parser = subparsers.add_parser("grep")
    _add_common_options(grep_parser)
    grep_parser.add_argument("--level", action="append", dest="levels")
    grep_parser.add_argument("--since")
    grep_parser.add_argument("--until")
    grep_parser.add_argument("--service")
    grep_parser.add_argument("--contains")
    grep_parser.add_argument("--limit", type=int)

    return parser


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file")
    parser.add_argument("--format", choices=["text", "json", "md"], default="text")
    parser.add_argument("--out")


def _clock() -> datetime:
    return datetime.now()


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "summary":
            return _run_summary(args)
        if args.command == "timeline":
            return _run_timeline(args)
        if args.command == "grep":
            return _run_grep(args)
    except (BucketValueError, FilterValueError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, CliRuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _run_summary(args: argparse.Namespace) -> int:
    result = summarise_file(args.file)
    if args.format == "text":
        print(format_summary_text(result))
        return 0
    if args.format == "json":
        print(format_summary_json(result, Path(args.file).name))
        return 0
    out_path = Path(args.out) if args.out else default_report_path("summary", _clock)
    print(write_summary_markdown(result, Path(args.file).name, out_path, _clock))
    return 0


def _run_timeline(args: argparse.Namespace) -> int:
    result = timeline_file(args.file, bucket=args.bucket, level=args.level)
    if args.format == "text":
        print(format_timeline_text(result))
        return 0
    if args.format == "json":
        print(format_timeline_json(result, Path(args.file).name))
        return 0
    out_path = Path(args.out) if args.out else default_report_path("timeline", _clock)
    print(write_timeline_markdown(result, Path(args.file).name, out_path, _clock))
    return 0


def _run_grep(args: argparse.Namespace) -> int:
    filters = build_filters(
        levels=args.levels,
        since=args.since,
        until=args.until,
        service=args.service,
        contains=args.contains,
        limit=args.limit,
    )
    result = grep_file(args.file, filters=filters)
    if args.format == "text":
        stdout, stderr = format_grep_text(result)
        if stdout:
            print(stdout)
        print(stderr, file=sys.stderr)
        return 0
    if args.format == "json":
        print(format_grep_json(result, Path(args.file).name))
        return 0
    out_path = Path(args.out) if args.out else default_report_path("grep", _clock)
    print(write_grep_markdown(result, Path(args.file).name, out_path, _clock))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
