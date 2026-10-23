# LogScope — Specification

## 1. Purpose

After an incident, the operations team needs a quick way to summarise an application log from the terminal, without opening a dashboard. LogScope is a command-line tool that processes a log file and produces summaries, timelines and filtered views as text, JSON or a Markdown report.

## 2. Scope

**In scope**
- Three commands: `summary`, `timeline`, `grep`
- Output formats: text (default), JSON, Markdown report file
- Streaming processing of large files (100 MB+)
- Tolerance of malformed lines
- A synthetic log generator and a performance benchmark
- A self-generated `samples/sample.log` committed to the repository for deterministic tests
- Stretch: `explain` command using an LLM endpoint

**Out of scope**
- Live tailing (`tail -f` style)
- Compressed input (`.gz`)
- Multiple input files in one invocation
- Any GUI or web dashboard

## 3. Technical constraints

- Python 3.11+
- Runtime uses the standard library only (`argparse`, `re`, `json`, `datetime`, `collections`, `urllib`)
- `pytest` is the only development dependency
- Installed as a console script: `logscope = logscope.cli:main`

## 4. Log format

Each valid line has this shape:

```
<date> <time> <LEVEL> [<service>] <message>
```

Example:

```
2026-10-01 09:00:12.345 ERROR [payment-api] Timeout calling bank gateway after 3000 ms (order_id=88123)
```

| Field | Rule |
|---|---|
| Timestamp | `YYYY-MM-DD HH:MM:SS`, optional fractional seconds `.f` (1–6 digits). Naive local time; no timezone. |
| Level | One of `INFO`, `WARN`, `WARNING`, `ERROR`. `WARNING` is normalised to `WARN`. Case-sensitive. |
| Service | Non-empty text inside square brackets, no `]`. |
| Message | Everything after `] `. May be empty. |

Reference pattern:

```
^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?) (INFO|WARN|WARNING|ERROR) \[([^\]]+)\] ?(.*)$
```

### 4.1 Malformed lines

A non-blank line is **malformed** if any of these is true:
- It does not match the pattern
- The timestamp matches the pattern but is not a real date/time (e.g. `2026-02-30`)
- It contains an unrecognised level (e.g. `DEBUG`, `TRACE`, `info`)

Malformed lines are counted and skipped. They must never raise an uncaught exception.

Additional rules:
- **Blank lines** (empty or whitespace only) are ignored and are not counted as malformed.
- **Encoding:** the file is read as UTF-8 with `errors="replace"`. Invalid bytes do not crash the tool.
- **Multi-line entries:** stack-trace continuation lines are counted as malformed. This is a known limitation and is reported, not hidden.

## 5. Commands

For each subcommand, the log file path is the first positional argument after the subcommand.

### 5.1 `logscope summary <file>`

Reports:
- **Line counts:** total lines read, valid lines, malformed lines, blank lines
- **Counts by level:** `INFO`, `WARN`, `ERROR` (always present, even when 0)
- **Time range:** earliest and latest valid timestamp. Lines may be out of order, so this uses the minimum and maximum, not the first and last line read.
- **Top 5 error messages:** the most frequent `ERROR` messages after normalisation (§5.1.1), each with its count, its service(s) and one raw example. Ties are broken alphabetically by normalised message.

#### 5.1.1 Message normalisation

So that similar errors group together, these are replaced in order before counting:

| Pattern | Replacement |
|---|---|
| UUIDs | `<uuid>` |
| Hex literals (`0x1f3a`) | `<hex>` |
| Numbers (integer or decimal) | `<n>` |

Example: `Timeout calling bank gateway after 3000 ms (order_id=88123)` → `Timeout calling bank gateway after <n> ms (order_id=<n>)`

#### 5.1.2 Memory bound

At most **10,000** distinct normalised error messages are tracked. After the cap is reached, errors with messages not already tracked are counted under a single `<other>` key. This keeps memory stable regardless of file size.

Services in `top_errors` are a sorted list of unique service names. The example is the first raw message seen in file order for that normalised error.

### 5.2 `logscope timeline <file> --bucket <duration>`

Shows the selected level count per time bucket as a text bar chart.

- `--bucket` accepts `<int><unit>` where unit is `s`, `m` or `h` (e.g. `30s`, `15m`, `1h`). Default `15m`. Invalid values cause a usage error.
- Buckets are aligned to the clock (a `15m` bucket starts at :00, :15, :30, :45).
- Every bucket from the first to the last bucket containing a valid line is shown, including buckets with zero counts.
- The displayed bucket range is determined by the earliest and latest valid timestamps in the file, regardless of the selected chart level.
- Bars are scaled so the largest bucket is 50 characters wide. Any non-zero count gets at least one character.
- `--level` optionally selects a different level to chart (default `ERROR`).

Example text output:

```
2026-10-01 09:00  ██████████                                          12
2026-10-01 09:15  ██████████████████████████████████████████████████  61
2026-10-01 09:30                                                       0
```

Memory: one counter per bucket. A 1-day log with `1m` buckets is 1,440 counters, which is acceptable. Bucket sizes under `1s` are rejected.

### 5.3 `logscope grep <file> [filters]`

Prints the original text of valid lines that match all given filters, in file order.

| Option | Meaning |
|---|---|
| `--level LEVEL` | Repeatable. Keep lines at this level (e.g. `--level ERROR --level WARN`). |
| `--since "YYYY-MM-DD HH:MM[:SS]"` | Keep lines with timestamp ≥ this value (inclusive). |
| `--until "YYYY-MM-DD HH:MM[:SS]"` | Keep lines with timestamp < this value (exclusive). |
| `--service NAME` | Keep lines from this service (exact match). |
| `--contains TEXT` | Keep lines whose message contains this text (case-sensitive). |
| `--limit N` | Stop after N matches. |

- With no filters, all valid lines are printed.
- Malformed lines are never printed.
- Lines are written as they are found, never collected first, so output starts immediately on large files.
- An invalid `--since` or `--until` value causes a usage error.
- When `--limit` is used, processing stops as soon as `N` matches are found. Reported counts reflect only the portion of the file processed up to that point.

## 6. Output formats

Every command accepts `--format text|json|md`. The default is `text`.

### 6.1 `text`
Human-readable output on stdout.
- For `summary` and `timeline`, the malformed-line count is part of the output.
- For `grep`, matched lines go to stdout and a one-line footer (`matched=N malformed=M`) goes to **stderr**, so piping stays clean.

### 6.2 `json`
A single JSON document on stdout. Every command's JSON includes:

```json
{
  "command": "summary",
  "file": "sample.log",
  "lines": { "total": 0, "valid": 0, "malformed": 0, "blank": 0 }
}
```

plus command-specific fields:
- `summary`: `levels`, `first_timestamp`, `last_timestamp`, `top_errors` (list of `{message, count, services, example}`)
- `timeline`: `bucket`, `level`, `buckets` (list of `{start, count}`)
- `grep`: `filters`, `matched`, `entries` (list of `{timestamp, level, service, message}`)

Timestamps use ISO 8601 (`2026-10-01T09:00:12.345000`). For `grep`, the `entries` array may be written incrementally by the formatter so matches do not need to be accumulated in memory before output.

### 6.3 `md`
Writes a Markdown report file and prints its path to stdout.
- Default filename: `logscope-<command>-<YYYYMMDD-HHMMSS>.md` in the current directory
- `--out PATH` overrides the filename
- The report includes the command, file name, generation time, line counts (including malformed) and the command's results (tables for summary, a fenced code block for the timeline chart and grep lines)
- For `grep`, matched lines must be written to the report incrementally; they must not be accumulated fully in memory before writing.

## 7. Errors and exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including when there are zero matches or all lines are malformed) |
| 1 | Runtime error: file not found, unreadable, cannot write report, LLM failure |
| 2 | Usage error: bad arguments, invalid `--bucket`, `--since` or `--until` |

Errors print a single clear message to stderr. No tracebacks for expected errors.

## 8. Performance

- Files are processed line by line. The tool never reads the whole file into memory (no `read()`, `readlines()` or `list(file)`).
- A 100 MB log is processed by each of `summary`, `timeline` and `grep --level ERROR` in **under 60 seconds** on a typical laptop.
- **Stable memory:** peak memory for a 100 MB file must be roughly the same as for a 10 MB file with the same mix of messages (within ~20%), showing memory does not grow with file size.

### 8.1 `scripts/gen_log.py`
Generates a synthetic log.
- `--size` target size (e.g. `100MB`, `10MB`), `--out` path
- `--malformed-rate` fraction of malformed lines (default `0.01`)
- `--seed` for reproducible output (default `42`)
- `--start` start timestamp; timestamps increase with small random gaps, with an occasional out-of-order line
- A realistic mix: mostly `INFO`, some `WARN`, a few percent `ERROR`, drawn from a set of templated messages with variable numbers and IDs, plus error bursts so the timeline shows spikes
- Malformed lines include: garbage text, missing level, bad date (`2026-13-45`), unknown level (`DEBUG`), truncated lines and stack-trace continuation lines
- It must also support generating a small deterministic `samples/sample.log` that is committed and used by tests.

### 8.2 `scripts/bench.py`
Runs each command against a given file and reports wall-clock time and peak memory (via `tracemalloc` so it works on Windows, macOS and Linux). Results are recorded in `BENCHMARK.md`.

Generated large files are not committed (`*.log` under `bench/` is git-ignored).

## 9. Sample data

`samples/sample.log` must be generated by the project author and then committed to the repository for deterministic testing. The generation process must be documented and reproducible.

The generated sample must include:
- `INFO`, `WARN`, `WARNING` and `ERROR` lines
- repeated `ERROR` messages with varying numbers and identifiers so normalisation can be tested
- malformed lines of different kinds
- blank lines
- at least one out-of-order valid timestamp
- an error burst in a bounded time range so timeline output has visible spikes
- timestamps suitable for `grep --since` / `--until` examples

## 10. Testing

- `pytest` unit tests for:
  - The parser: valid lines, each malformed case, `WARNING` normalisation, fractional seconds, blank lines, invalid bytes
  - Normalisation
  - Each command's logic, using small inline fixtures with known expected results
  - Each output format for each command
  - CLI error handling and exit codes
- An end-to-end test that runs all three commands against `samples/sample.log`
- Tests must not depend on the current time (inject the clock for report filenames)

## 11. Acceptance criteria

- [ ] `summary`, `timeline` and `grep` work on `samples/sample.log` in all three formats
- [ ] Unit tests exist for the parser and each command, and all pass
- [ ] A 100 MB log is processed in under 60 seconds with stable memory, recorded in `BENCHMARK.md`
- [ ] The malformed-line count is reported by every command
- [ ] Git history shows a committed plan followed by incremental build commits, not one large commit

## 12. Stretch: `logscope explain <file>`

Sends the top errors to an LLM and prints a probable root-cause summary.

- Configuration via environment variables:
  - `LOGSCOPE_LLM_URL` — an OpenAI-compatible chat-completions endpoint (required)
  - `LOGSCOPE_LLM_API_KEY` — bearer token (optional)
  - `LOGSCOPE_LLM_MODEL` — model name (required)
- Builds the summary (§5.1), then sends the top 5 errors with counts, services, examples, the time range and the error timeline peak.
- Only these aggregated details are sent, never the raw log file.
- If `LOGSCOPE_LLM_URL` is unset, print a clear message explaining how to configure it and exit with code 1.
- Network errors and timeouts (30 s) produce a clear message and exit code 1.
- Uses `urllib` from the standard library. Tests mock the HTTP call and never hit a real endpoint.
- Supports `--format text|json|md` like the other commands.
- This stretch goal is non-blocking for core assignment acceptance.

## 13. Project layout

```
logscope/
├── SPEC.md
├── INSTRUCTIONS.md
├── PLAN.md
├── BENCHMARK.md
├── pyproject.toml
├── src/logscope/
│   ├── __init__.py
│   ├── cli.py          # argparse, dispatch, exit codes
│   ├── parser.py       # line parsing, LogEntry, malformed handling
│   ├── normalise.py    # message normalisation
│   ├── summary.py
│   ├── timeline.py
│   ├── grep.py
│   ├── formatters.py   # text / json / md
│   └── explain.py      # stretch
├── scripts/
│   ├── gen_log.py
│   └── bench.py
├── samples/
│   └── sample.log
└── tests/
```
