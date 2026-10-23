from datetime import datetime
from pathlib import Path

from logscope.cli import main
from scripts.gen_log import generate_log


def test_end_to_end_commands_on_generated_sample(tmp_path: Path, capsys) -> None:
    sample = tmp_path / "sample.log"
    generate_log(
        out_path=sample,
        target_bytes=4096,
        malformed_rate=0.02,
        seed=7,
        start=datetime(2026, 10, 1, 8, 0, 0),
    )

    assert main(["summary", str(sample)]) == 0
    assert "Summary" in capsys.readouterr().out

    assert main(["timeline", str(sample), "--bucket", "15m"]) == 0
    assert "Timeline" in capsys.readouterr().out

    assert main(["grep", str(sample), "--level", "ERROR"]) == 0
    captured = capsys.readouterr()
    assert "matched=" in captured.err
