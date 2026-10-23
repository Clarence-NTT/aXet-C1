from datetime import datetime
import json
from pathlib import Path

from logscope.cli import main
from logscope.grep import GrepFilters, grep_stream
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
from logscope.summary import summarise_stream
from logscope.timeline import timeline_stream


def _clock() -> datetime:
    return datetime(2026, 10, 1, 12, 0, 0)


def test_summary_formatters_cover_text_json_and_markdown(tmp_path: Path) -> None:
    result = summarise_stream(
        [
            "2026-10-01 09:00:00 INFO [api] ready\n",
            "2026-10-01 09:01:00 ERROR [api] timeout 1\n",
        ]
    )

    text_output = format_summary_text(result)
    json_output = json.loads(format_summary_json(result, "sample.log"))
    report_path = write_summary_markdown(result, "sample.log", tmp_path / "summary.md", _clock)

    assert "Summary" in text_output
    assert json_output["command"] == "summary"
    assert report_path.read_text(encoding="utf-8").startswith("# LogScope summary report")


def test_timeline_formatters_cover_text_json_and_markdown(tmp_path: Path) -> None:
    result = timeline_stream(
        [
            "2026-10-01 09:00:00 ERROR [api] fail\n",
            "2026-10-01 09:15:00 ERROR [api] fail\n",
        ],
        bucket="15m",
    )

    text_output = format_timeline_text(result)
    json_output = json.loads(format_timeline_json(result, "sample.log"))
    report_path = write_timeline_markdown(result, "sample.log", tmp_path / "timeline.md", _clock)

    assert "Timeline level=ERROR bucket=15m" in text_output
    assert json_output["command"] == "timeline"
    assert "```text" in report_path.read_text(encoding="utf-8")


def test_grep_formatters_cover_text_json_and_markdown(tmp_path: Path) -> None:
    result = grep_stream(
        [
            "2026-10-01 09:00:00 ERROR [api] fail\n",
            "bad line\n",
        ],
        filters=GrepFilters(),
    )

    stdout, stderr = format_grep_text(result)
    json_output = json.loads(format_grep_json(result, "sample.log"))
    report_path = write_grep_markdown(result, "sample.log", tmp_path / "grep.md", _clock)

    assert "2026-10-01 09:00:00 ERROR [api] fail" in stdout
    assert stderr == "matched=1 malformed=1"
    assert json_output["command"] == "grep"
    assert "Matched lines" in report_path.read_text(encoding="utf-8")


def test_default_report_path_uses_clock() -> None:
    assert str(default_report_path("summary", _clock)) == "logscope-summary-20261001-120000.md"


def test_cli_runs_summary_in_text_mode(tmp_path: Path, capsys) -> None:
    log_file = tmp_path / "sample.log"
    log_file.write_text("2026-10-01 09:00:00 INFO [api] ready\n", encoding="utf-8")

    exit_code = main(["summary", str(log_file)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Summary" in captured.out
    assert captured.err == ""


def test_cli_runs_timeline_in_json_mode(tmp_path: Path, capsys) -> None:
    log_file = tmp_path / "sample.log"
    log_file.write_text("2026-10-01 09:00:00 ERROR [api] fail\n", encoding="utf-8")

    exit_code = main(["timeline", str(log_file), "--format", "json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["command"] == "timeline"


def test_cli_runs_grep_in_text_mode_with_footer_on_stderr(tmp_path: Path, capsys) -> None:
    log_file = tmp_path / "sample.log"
    log_file.write_text(
        "2026-10-01 09:00:00 ERROR [api] fail\n2026-10-01 09:01:00 INFO [api] ok\n",
        encoding="utf-8",
    )

    exit_code = main(["grep", str(log_file), "--level", "ERROR"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "ERROR [api] fail" in captured.out
    assert captured.err.strip() == "matched=1 malformed=0"


def test_cli_writes_markdown_report(tmp_path: Path, capsys) -> None:
    log_file = tmp_path / "sample.log"
    report_file = tmp_path / "report.md"
    log_file.write_text("2026-10-01 09:00:00 INFO [api] ready\n", encoding="utf-8")

    exit_code = main(["summary", str(log_file), "--format", "md", "--out", str(report_file)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert str(report_file) in captured.out
    assert report_file.exists()


def test_cli_returns_usage_error_for_invalid_filters(tmp_path: Path, capsys) -> None:
    log_file = tmp_path / "sample.log"
    log_file.write_text("2026-10-01 09:00:00 INFO [api] ready\n", encoding="utf-8")

    exit_code = main(["grep", str(log_file), "--since", "bad"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "invalid datetime" in captured.err


def test_cli_returns_runtime_error_for_missing_file(capsys) -> None:
    exit_code = main(["summary", "missing.log"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No such file" in captured.err
