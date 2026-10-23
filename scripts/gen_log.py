"""Generate synthetic logs for samples and benchmarks."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random

SERVICES = ["api", "payment-api", "worker", "auth", "checkout"]
INFO_MESSAGES = [
    "Request completed in {duration} ms",
    "User {user_id} authenticated successfully",
    "Cache refreshed for tenant {tenant_id}",
]
WARN_MESSAGES = [
    "Queue depth reached {count}",
    "Retrying partner call after {duration} ms",
    "WARNING token rotation due in {count} minutes",
]
ERROR_MESSAGES = [
    "Timeout calling bank gateway after {duration} ms (order_id={order_id})",
    "Database deadlock detected on shard {shard_id}",
    "Downstream 502 from partner {partner_id} trace={trace_id}",
]
MALFORMED_LINES = [
    "garbage text with no structure",
    "2026-13-45 09:00:00 INFO [api] impossible date",
    "2026-10-01 09:00:00 DEBUG [api] unsupported level",
    "2026-10-01 09:00:00 INFO missing service",
    "Traceback: ValueError: boom",
]


def parse_size(value: str) -> int:
    """Parse a human-readable size into bytes."""
    suffixes = {"KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}
    upper = value.upper()
    for suffix, factor in suffixes.items():
        if upper.endswith(suffix):
            return int(float(value[:-2]) * factor)
    return int(value)


def _format_line(timestamp: datetime, level: str, service: str, message: str) -> str:
    return f"{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} {level} [{service}] {message}"


def _random_message(rng: random.Random, template: str) -> str:
    return template.format(
        duration=rng.randint(5, 5000),
        user_id=rng.randint(1000, 9999),
        tenant_id=rng.randint(10, 99),
        count=rng.randint(1, 500),
        order_id=rng.randint(10000, 99999),
        shard_id=rng.randint(1, 16),
        partner_id=rng.randint(100, 999),
        trace_id=f"0x{rng.randint(0, 65535):04x}",
    )


def generate_log(
    *,
    out_path: Path,
    target_bytes: int,
    malformed_rate: float,
    seed: int,
    start: datetime,
) -> None:
    """Generate a synthetic log file to approximately the target size."""
    rng = random.Random(seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    current = start
    bytes_written = 0
    line_number = 0
    required_prefix = [
        _format_line(start, "INFO", "api", "Request completed in 42 ms"),
        _format_line(start + timedelta(seconds=5), "WARNING", "worker", "Queue depth reached 17"),
        _format_line(start + timedelta(seconds=10), "ERROR", "payment-api", "Timeout calling bank gateway after 3000 ms (order_id=88123)"),
        "garbage text with no structure",
        "",
    ]
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for line in required_prefix:
            encoded = f"{line}\n"
            handle.write(encoded)
            bytes_written += len(encoded.encode("utf-8"))
        current = start + timedelta(seconds=15)
        while bytes_written < target_bytes:
            line_number += 1
            roll = rng.random()
            if roll < malformed_rate:
                line = rng.choice(MALFORMED_LINES)
            elif roll < malformed_rate + 0.015:
                line = ""
            else:
                service = rng.choice(SERVICES)
                if 240 <= line_number % 480 <= 320:
                    level = "ERROR"
                else:
                    level = rng.choices(["INFO", "WARNING", "WARN", "ERROR"], weights=[78, 5, 12, 5])[0]
                template_pool = {
                    "INFO": INFO_MESSAGES,
                    "WARNING": WARN_MESSAGES,
                    "WARN": WARN_MESSAGES,
                    "ERROR": ERROR_MESSAGES,
                }
                message = _random_message(rng, rng.choice(template_pool[level]))
                timestamp = current
                if line_number % 211 == 0:
                    timestamp = current - timedelta(seconds=rng.randint(5, 45))
                line = _format_line(timestamp, level, service, message)
            encoded = f"{line}\n"
            handle.write(encoded)
            bytes_written += len(encoded.encode("utf-8"))
            current += timedelta(seconds=rng.randint(1, 6), milliseconds=rng.randint(0, 900))


def build_parser() -> argparse.ArgumentParser:
    """Build the generator CLI parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--malformed-rate", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", default="2026-10-01T08:00:00")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the log generator."""
    args = build_parser().parse_args(argv)
    generate_log(
        out_path=Path(args.out),
        target_bytes=parse_size(args.size),
        malformed_rate=args.malformed_rate,
        seed=args.seed,
        start=datetime.fromisoformat(args.start),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
