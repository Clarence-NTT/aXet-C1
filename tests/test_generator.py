from datetime import datetime
from pathlib import Path

from scripts.gen_log import generate_log, parse_size


def test_parse_size_supports_plain_numbers_and_suffixes() -> None:
    assert parse_size("1024") == 1024
    assert parse_size("1KB") == 1024
    assert parse_size("1MB") == 1024 * 1024


def test_generate_log_creates_content(tmp_path: Path) -> None:
    output = tmp_path / "sample.log"

    generate_log(
        out_path=output,
        target_bytes=2048,
        malformed_rate=0.05,
        seed=42,
        start=datetime(2026, 10, 1, 8, 0, 0),
    )

    text = output.read_text(encoding="utf-8")
    assert output.exists()
    assert output.stat().st_size >= 2048
    assert "ERROR" in text
    assert "WARNING" in text or "WARN" in text
