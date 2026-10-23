# LogScope Implementation Plan

## Step 1 — Parser and normalisation
- Create project skeleton in `src/logscope/` and `tests/`.
- Implement `LogEntry` data model and line parser in `parser.py`.
- Support UTF-8 with replacement, blank-line handling, malformed detection, timestamp parsing, and `WARNING` → `WARN` normalisation.
- Implement message normalisation in `normalise.py` for UUIDs, hex literals, and numbers.
- Add parser and normaliser unit tests covering valid lines, malformed cases, blank lines, fractional seconds, and invalid bytes.

## Step 2 — Summary
- Implement streaming summary logic in `summary.py`.
- Track line counts, level counts, time range, and top 5 normalised error groups with bounded memory.
- Add tests for counts, out-of-order timestamps, message grouping, tie-breaking, service sorting, and `<other>` overflow behaviour.

## Step 3 — Timeline
- Implement bucket parsing and aligned bucket aggregation in `timeline.py`.
- Support `--bucket` units `s`, `m`, `h` and optional `--level`.
- Produce zero-filled buckets from first to last valid timestamp.
- Add tests for bucket alignment, empty buckets, scaling inputs, invalid bucket values, and alternate levels.

## Step 4 — Grep
- Implement streaming filtering in `grep.py`.
- Support filters for repeated `--level`, `--since`, `--until`, `--service`, `--contains`, and `--limit`.
- Preserve file order, count malformed lines, and stop early on limit.
- Add tests for each filter, combined filters, zero matches, all-malformed input, and limit semantics.

## Step 5 — Output formats and CLI
- Implement formatters for text, JSON, and Markdown in `formatters.py`.
- Stream `grep` JSON and Markdown output incrementally.
- Build argparse CLI in `cli.py` with required exit codes and clear stderr messages.
- Add tests for every command in every output format, Markdown report writing, and CLI error handling.

## Step 6 — Sample generator
- Implement `scripts/gen_log.py` to generate deterministic sample and large benchmark logs.
- Generate and commit `samples/sample.log` with required valid, malformed, blank, and bursty content.
- Add tests for generator helpers where practical.

## Step 7 — Benchmark
- Implement `scripts/bench.py` using `tracemalloc` and subprocess timing.
- Benchmark 10 MB and 100 MB logs and record results in `BENCHMARK.md`.
- Update `.gitignore` to exclude large generated logs and Markdown reports.

## Step 8 — Stretch explain
- Implement `explain.py` using `urllib` and environment variables.
- Reuse summary outputs and send only aggregated data.
- Add mocked tests for configuration errors and HTTP success/failure paths.

## Execution notes
- Follow the exact step order in `INSTRUCTIONS.md`.
- After each completed step: run `pytest -q`, fix failures, commit with a conventional commit message, and stop.
- Run all build/test commands through WSL Ubuntu in the project directory.
