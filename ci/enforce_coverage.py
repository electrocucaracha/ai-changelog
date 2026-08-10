#!/usr/bin/env python3
"""Fail CI when measured code coverage falls below the required threshold."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for coverage enforcement."""
    parser = argparse.ArgumentParser(
        description="Fail when code coverage is below the required threshold."
    )
    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to the coverage JSON report (default: coverage.json).",
    )
    return parser.parse_args()


def main() -> int:
    """Run the coverage enforcement check."""
    args = parse_args()
    threshold = float(os.environ.get("COVERAGE_THRESHOLD", "95"))
    cov = json.loads(Path(args.coverage_file).read_text(encoding="utf-8"))
    totals = cov["totals"]
    coverage = float(
        totals.get("percent_covered", totals.get("percent_covered_display", 0))
    )

    print(f"Coverage: {coverage:.2f}% (threshold: {threshold:.2f}%)")
    if coverage < threshold:
        print(
            f"ERROR: Coverage {coverage:.2f}% is below required {threshold:.2f}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
