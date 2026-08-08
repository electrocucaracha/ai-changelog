#!/usr/bin/env python3
"""Aggregate mutmut stats artifacts and fail CI on surviving mutations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for mutation gate checks."""
    parser = argparse.ArgumentParser(
        description="Check mutmut stats and fail when survived/suspicious mutations exist."
    )
    parser.add_argument(
        "--stats-dir",
        default="mutmut-stats",
        help="Directory where mutmut artifacts were downloaded.",
    )
    return parser.parse_args()


def collect_stats_files(stats_dir: Path) -> list[Path]:
    """Return all mutmut stats files found under stats_dir."""
    return sorted(stats_dir.rglob("mutmut-cicd-stats.json"))


def parse_int_stat(stats: dict[str, object], key: str) -> int:
    """Parse integer stats defensively for clearer error output."""
    value = stats.get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid numeric value for '{key}': {value!r}") from None


def summarize_file(stats_file: Path) -> tuple[int, int]:
    """Print per-file mutation summary and return survived/suspicious counts."""
    raw_text = stats_file.read_text(encoding="utf-8")
    try:
        stats = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse JSON in {stats_file}: {exc.msg} at line {exc.lineno}"
        ) from exc

    survived = parse_int_stat(stats, "survived")
    suspicious = parse_int_stat(stats, "suspicious")
    killed = parse_int_stat(stats, "killed")
    timeout = parse_int_stat(stats, "timeout")
    no_tests = parse_int_stat(stats, "no_tests")

    print(
        " -"
        f" {stats_file}: survived={survived}, suspicious={suspicious},"
        f" killed={killed}, timeout={timeout}, no_tests={no_tests}"
    )
    return survived, suspicious


def main() -> int:
    """Run the mutation gate check."""
    args = parse_args()
    stats_dir = Path(args.stats_dir)

    if not stats_dir.exists():
        print(
            f"ERROR: Stats directory '{stats_dir}' does not exist. "
            "Did artifact download fail?",
            file=sys.stderr,
        )
        return 1

    stats_files = collect_stats_files(stats_dir)
    print(f"Found {len(stats_files)} mutmut stats file(s) under {stats_dir}")

    if not stats_files:
        print(
            "ERROR: No mutmut stats files found. "
            "Expected files named mutmut-cicd-stats.json.",
            file=sys.stderr,
        )
        return 1

    total_survived = 0
    total_suspicious = 0

    for stats_file in stats_files:
        try:
            survived, suspicious = summarize_file(stats_file)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        total_survived += survived
        total_suspicious += suspicious

    print(
        "Mutation totals:"
        f" survived={total_survived}, suspicious={total_suspicious}"
    )

    if total_survived or total_suspicious:
        print(
            "Mutation test gate failed: "
            f"survived={total_survived}, suspicious={total_suspicious}",
            file=sys.stderr,
        )
        return 1

    print("Mutation test gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
