#!/usr/bin/env python3
"""Fail CI when the aggregate mutation score falls below the required threshold."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for mutation score enforcement."""
    parser = argparse.ArgumentParser(
        description="Fail when the mutation score is below the required threshold."
    )
    parser.add_argument(
        "--stats-dir",
        default="mutmut-stats",
        help="Directory where mutmut artifact files were downloaded.",
    )
    return parser.parse_args()


def collect_stats_files(stats_dir: Path) -> list[Path]:
    """Return all mutmut stats files found under stats_dir."""
    return sorted(stats_dir.rglob("mutmut-cicd-stats.json"))


def aggregate_totals(files: list[Path]) -> dict[str, int]:
    """Sum mutation counters across all stats files."""
    totals: dict[str, int] = {
        k: 0 for k in ("killed", "survived", "suspicious", "timeout", "no_tests")
    }
    for stats_file in files:
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
        for key in totals:
            totals[key] += int(stats.get(key, 0))
    return totals


def main() -> int:
    """Run the mutation score enforcement check."""
    args = parse_args()
    stats_dir = Path(args.stats_dir)
    threshold = float(os.environ.get("MUTATION_THRESHOLD", "95"))

    if not stats_dir.exists():
        print(
            f"ERROR: Stats directory '{stats_dir}' does not exist. "
            "Did artifact download fail?",
            file=sys.stderr,
        )
        return 1

    files = collect_stats_files(stats_dir)
    if not files:
        print(
            "ERROR: No mutmut stats files found. "
            "Expected files named mutmut-cicd-stats.json.",
            file=sys.stderr,
        )
        return 1

    totals = aggregate_totals(files)
    attempted = (
        totals["killed"] + totals["survived"] + totals["suspicious"] + totals["timeout"]
    )
    if attempted == 0:
        print("ERROR: No mutation attempts found in stats.", file=sys.stderr)
        return 1

    mutation_score = (totals["killed"] / attempted) * 100
    print(f"Mutation score: {mutation_score:.2f}% (threshold: {threshold:.2f}%)")
    print(
        f"Totals: killed={totals['killed']}, survived={totals['survived']}, "
        f"suspicious={totals['suspicious']}, timeout={totals['timeout']}, "
        f"no_tests={totals['no_tests']}"
    )

    if mutation_score < threshold:
        print(
            f"ERROR: Mutation score {mutation_score:.2f}% is below required {threshold:.2f}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
