# Project instructions — LogScope

You are working on LogScope, a Python CLI that summarises application logs. **SPEC.md is the source of truth.** Read it before making any change. If a request conflicts with SPEC.md, stop and ask; do not silently change the spec.

## Stack

- Python 3.11+
- Runtime: standard library only. Do not add runtime dependencies.
- Dev: `pytest` only. Ask before adding any other package.
- Source in `src/logscope/`, tests in `tests/`, scripts in `scripts/`.

## Commands

```bash
# Setup (once)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -e . pytest

# Test
pytest -q

# Run
logscope summary samples/sample.log
logscope timeline samples/sample.log --bucket 15m
logscope grep samples/sample.log --level ERROR --since "2026-10-01 09:00"

# Generate a large log and benchmark it
python scripts/gen_log.py --size 100MB --out bench/big.log
python scripts/bench.py bench/big.log
```

## Workflow rules

1. **Plan first.** When asked for a plan, write it to `PLAN.md` and stop. Do not write any code until the plan has been reviewed and explicitly approved.
2. **Build one step at a time,** in this order:
   1. Parser (+ normalisation)
   2. `summary`
   3. `timeline`
   4. `grep`
   5. Output formats (`json`, `md`)
   6. Generator and benchmark
   7. Stretch: `explain`
3. **Each step:** write the tests and code for that step only → run `pytest -q` → fix until all tests pass → commit → stop and report what was done.
4. **Never commit with failing tests.** Never skip, delete or weaken a test to make it pass. If a test seems wrong, explain why and ask.
5. **Do not start the next step** until told to.
6. If you are unsure about behaviour the spec does not cover, ask rather than guess. Note any agreed decisions in SPEC.md.

## Commits

- One commit per step (small fix-up commits are fine).
- Conventional-commit style messages:
  - `docs: add SPEC and agent instructions`
  - `docs: add implementation plan`
  - `feat(parser): parse log lines and count malformed`
  - `feat(summary): level counts, time range, top errors`
  - `test(timeline): cover empty buckets and bar scaling`
  - `perf: add 100MB generator and benchmark results`
- Do not commit generated large files, `.venv/` or report files (`logscope-*.md`).

## Hard rules for the code

- **Stream, never slurp.** Iterate the file line by line. Never use `.read()`, `.readlines()`, `list(f)` or anything else that loads the whole file.
- **Malformed lines never crash.** The parser returns `None` (or equivalent) for a bad line, and the caller counts it. Wrap only the parsing of a single line; do not use broad `try/except` around whole commands.
- Open files with `encoding="utf-8", errors="replace"`.
- **Bounded memory.** Any per-message collection must respect the cap in SPEC.md §5.1.2. Do not accumulate lines or entries in lists.
- **Keep logic separate from I/O.** Command modules return plain data (dicts or dataclasses), or iterables of plain data for streaming commands. `formatters.py` turns that data into text, JSON or Markdown. For streaming commands such as `grep`, formatters may consume iterators and write incrementally.
- Expected errors (missing file, bad arguments) print one clear line to stderr and use the exit codes in SPEC.md §7. No tracebacks.
- Type hints on public functions. Short docstrings. No dead code.

## Testing rules

- Every module has a test file (`tests/test_parser.py`, `tests/test_summary.py`, …).
- Use small inline fixtures (a few lines in a string or `tmp_path` file) with exact expected values.
- Cover the edge cases in SPEC.md: every malformed type, blank lines, invalid bytes, `WARNING` → `WARN`, out-of-order timestamps, empty buckets, zero matches, an all-malformed file.
- Tests must not depend on the current time or network access.

## Performance check

When running the benchmark, record the following in `BENCHMARK.md`:
- Machine details
- File sizes (10 MB and 100 MB)
- Time and peak memory for each command

The 100 MB run must be under 60 s, and peak memory must not grow meaningfully between 10 MB and 100 MB. If it does, find the cause before moving on.
