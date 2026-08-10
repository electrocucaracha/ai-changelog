#!/usr/bin/env python3
"""Write a code-coverage Markdown table to the GitHub Actions job summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for coverage summary publishing."""
    parser = argparse.ArgumentParser(
        description="Append a coverage Markdown table to GITHUB_STEP_SUMMARY."
    )
    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to the coverage JSON report (default: coverage.json).",
    )
    return parser.parse_args()


def build_summary(cov: dict) -> str:
    """Return the Markdown summary string for the given coverage data."""
    totals = cov["totals"]
    rows = []
    for fname, data in sorted(cov["files"].items()):
        s = data["summary"]
        rows.append(
            f"| {fname} | {s['num_statements']} | {s['covered_lines']} "
            f"| {s['missing_lines']} | {s['percent_covered_display']}% |"
        )
    lines = [
        "## Code Coverage",
        "",
        "| File | Statements | Covered | Missing | Coverage |",
        "|------|-----------|---------|---------|----------|",
        *rows,
        "",
        (
            f"**Total: {totals['covered_lines']}/{totals['num_statements']} "
            f"lines ({totals['percent_covered_display']}%)**"
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Publish the coverage summary to the GitHub Actions job summary."""
    args = parse_args()
    cov = json.loads(Path(args.coverage_file).read_text(encoding="utf-8"))
    summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(build_summary(cov))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
