"""Benchmark LogScope commands."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

COMMANDS = [
    ["summary"],
    ["timeline", "--bucket", "15m"],
    ["grep", "--level", "ERROR"],
]


def run_command(project_dir: Path, log_file: Path, command: list[str]) -> tuple[float, int]:
    """Run one CLI command and return duration and peak memory."""
    tracemalloc.start()
    started = time.perf_counter()
    subprocess.run(
        [sys.executable, "-m", "logscope", *command, str(log_file)],
        cwd=project_dir,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    duration = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return duration, peak


def write_benchmark(project_dir: Path, log_file: Path) -> Path:
    """Run benchmarks and write BENCHMARK.md."""
    rows: list[str] = []
    for command in COMMANDS:
        duration, peak = run_command(project_dir, log_file, command)
        rows.append(
            f"| {' '.join(command)} | {duration:.2f} | {peak / (1024 * 1024):.2f} |"
        )
    output = project_dir / "BENCHMARK.md"
    content = [
        "# Benchmark results",
        "",
        f"- Generated at: `{datetime.now().isoformat()}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- File: `{log_file}`",
        "",
        "| Command | Seconds | Peak MB |",
        "|---|---:|---:|",
        *rows,
        "",
    ]
    output.write_text("\n".join(content), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log_file")
    args = parser.parse_args(argv)
    write_benchmark(Path.cwd(), Path(args.log_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
