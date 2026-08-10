#!/usr/bin/env python3
"""Write a per-module mutation result table to the GitHub Actions job summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for per-module mutation summary publishing."""
    parser = argparse.ArgumentParser(
        description="Append a per-module mutation result table to GITHUB_STEP_SUMMARY."
    )
    parser.add_argument(
        "--module",
        required=True,
        help="Module name being tested (used as the section heading).",
    )
    parser.add_argument(
        "--stats-file",
        default="mutants/mutmut-cicd-stats.json",
        help="Path to the mutmut stats JSON file (default: mutants/mutmut-cicd-stats.json).",
    )
    return parser.parse_args()


def build_summary(module: str, stats: dict) -> str:
    """Return the Markdown summary string for the given module mutation stats."""
    lines = [
        f"## Mutation Test Results \u2014 {module}",
        "",
        "| Killed | Survived | Suspicious | Timeout | No Tests |",
        "|--------|----------|------------|---------|----------|",
        (
            f"| {stats.get('killed', 0)} | {stats.get('survived', 0)} "
            f"| {stats.get('suspicious', 0)} | {stats.get('timeout', 0)} "
            f"| {stats.get('no_tests', 0)} |"
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Publish the per-module mutation summary to the GitHub Actions job summary."""
    args = parse_args()
    stats = json.loads(Path(args.stats_file).read_text(encoding="utf-8"))
    summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(build_summary(args.module, stats))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
