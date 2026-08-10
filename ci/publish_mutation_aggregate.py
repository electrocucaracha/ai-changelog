#!/usr/bin/env python3
"""Write an aggregate mutation results table to the GitHub Actions job summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for aggregate mutation summary publishing."""
    parser = argparse.ArgumentParser(
        description="Append an aggregate mutation results table to GITHUB_STEP_SUMMARY."
    )
    parser.add_argument(
        "--stats-dir",
        default="mutmut-stats",
        help="Directory where mutmut artifact files were downloaded.",
    )
    return parser.parse_args()


def build_summary(files: list[Path], threshold: float) -> str:
    """Return the Markdown summary string for the aggregated mutation stats."""
    totals: dict[str, int] = {
        k: 0 for k in ("killed", "survived", "suspicious", "timeout", "no_tests")
    }
    rows = []
    for f in files:
        module = f.parent.name.removeprefix("mutmut-stats-")
        s = json.loads(f.read_text(encoding="utf-8"))
        for k in totals:
            totals[k] += int(s.get(k, 0))
        rows.append(
            f"| {module} | {s.get('killed', 0)} | {s.get('survived', 0)} "
            f"| {s.get('suspicious', 0)} | {s.get('timeout', 0)} "
            f"| {s.get('no_tests', 0)} |"
        )

    attempted = (
        totals["killed"] + totals["survived"] + totals["suspicious"] + totals["timeout"]
    )
    mutation_score = (totals["killed"] / attempted * 100) if attempted else 0.0

    total_row = (
        f"| **Total** | **{totals['killed']}** | **{totals['survived']}** "
        f"| **{totals['suspicious']}** | **{totals['timeout']}** "
        f"| **{totals['no_tests']}** |"
    )
    lines = [
        "## Mutation Test Results",
        "",
        "| Module | Killed | Survived | Suspicious | Timeout | No Tests |",
        "|--------|--------|----------|------------|---------|----------|",
        *rows,
        total_row,
        "",
        f"**Mutation score: {mutation_score:.2f}% (threshold: {threshold:.2f}%)**",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Publish the aggregate mutation summary to the GitHub Actions job summary."""
    args = parse_args()
    stats_dir = Path(args.stats_dir)
    threshold = float(os.environ.get("MUTATION_THRESHOLD", "95"))
    files = sorted(stats_dir.rglob("mutmut-cicd-stats.json"))
    summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(build_summary(files, threshold))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
