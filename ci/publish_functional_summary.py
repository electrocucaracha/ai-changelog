#!/usr/bin/env python3
"""Publish functional test and token usage details to GitHub Actions summary."""

from __future__ import annotations

import argparse
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_FAILURE_DETAILS = 3


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for functional summary publishing."""
    parser = argparse.ArgumentParser(
        description=(
            "Append functional test results and LLMock token usage "
            "to GITHUB_STEP_SUMMARY."
        )
    )
    parser.add_argument(
        "--junit-file",
        default="functional-junit.xml",
        help="Path to the JUnit XML report (default: functional-junit.xml).",
    )
    parser.add_argument(
        "--llmock-log",
        default="llmock.log",
        help="Path to the LLMock log file (default: llmock.log).",
    )
    parser.add_argument(
        "--tests-log",
        default="functional-tests.log",
        help="Path to the pytest output log (default: functional-tests.log).",
    )
    parser.add_argument(
        "--test-exit-code",
        type=int,
        default=None,
        help=(
            "Functional test exit code. "
            "If omitted, uses TEST_EXIT_CODE env var (default: 1)."
        ),
    )
    return parser.parse_args()


def parse_junit_totals(junit_file: Path) -> tuple[int, int, int, int]:
    """Return total tests, failures, errors, and skipped from a JUnit XML file."""
    if not junit_file.exists():
        return 0, 0, 0, 0

    root = ET.parse(junit_file).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

    tests = failures = errors = skipped = 0
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0))
        errors += int(suite.attrib.get("errors", 0))
        skipped += int(suite.attrib.get("skipped", 0))
    return tests, failures, errors, skipped


def parse_token_usage(llmock_log: Path) -> tuple[dict[str, int], int]:
    """Extract aggregate token usage and matched event count from LLMock logs."""
    totals: dict[str, int] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    if not llmock_log.exists():
        return totals, 0

    content = llmock_log.read_text(encoding="utf-8", errors="ignore")
    hits = 0
    for key in totals:
        pattern = re.compile(rf'"{key}"\s*[:=]\s*(\d+)')
        values = [int(value) for value in pattern.findall(content)]
        if values:
            totals[key] = sum(values)
            hits += len(values)
    return totals, hits


def parse_failed_testcases(junit_file: Path) -> list[tuple[str, str]]:
    """Return failed/error testcases from JUnit as (name, message) tuples."""
    if not junit_file.exists():
        return []

    root = ET.parse(junit_file).getroot()
    testcases = root.findall(".//testcase")
    failures: list[tuple[str, str]] = []
    for testcase in testcases:
        classname = testcase.attrib.get("classname", "")
        name = testcase.attrib.get("name", "unknown")
        display_name = f"{classname}.{name}" if classname else name

        failed_node = testcase.find("failure")
        error_node = testcase.find("error")
        detail_node = failed_node or error_node
        if detail_node is None:
            continue

        message = detail_node.attrib.get("message", "").strip()
        body = (detail_node.text or "").strip()
        excerpt = message
        if not excerpt and body:
            excerpt = body.splitlines()[0]
        if not excerpt:
            excerpt = "(no details)"
        failures.append((display_name, excerpt[:300]))
    return failures


def detect_troubleshooting_hints(tests_log: Path, llmock_log: Path) -> list[str]:
    """Return heuristic hints to speed up root-cause analysis."""
    hints: list[str] = []
    tests_content = ""
    llmock_content = ""
    if tests_log.exists():
        tests_content = tests_log.read_text(encoding="utf-8", errors="ignore")
    if llmock_log.exists():
        llmock_content = llmock_log.read_text(encoding="utf-8", errors="ignore")

    combined = f"{tests_content}\n{llmock_content}"
    lower = combined.lower()

    if "blocked due to security risk" in lower:
        hints.append(
            "Detected enterprise web-gateway interception for localhost requests; "
            "verify no proxy is applied to 127.0.0.1/localhost inside test runtime."
        )
    if "failed to connect" in lower or "connection refused" in lower:
        hints.append(
            "Detected connection failures to LLMock endpoint; verify mock process "
            "is still running and responding on http://127.0.0.1:8001/ping."
        )
    if "apierror" in lower and "chat/completions" in lower:
        hints.append(
            "LLM API call failed on chat completions; inspect request base URL and "
            "ensure LLMock endpoint path matches '/chatgpt/chat/completions'."
        )
    if not hints and tests_log.exists() and not llmock_log.exists():
        hints.append("LLMock log file is missing; check mock startup/redirect step.")
    return hints


def build_summary(
    test_exit_code: int,
    tests: int,
    failures: int,
    errors: int,
    skipped: int,
    token_totals: dict[str, int],
    token_hits: int,
    failed_testcases: list[tuple[str, str]],
    troubleshooting_hints: list[str],
) -> str:
    """Build the markdown content for functional test and token usage summary."""
    status = "PASSED" if test_exit_code == 0 else "FAILED"
    lines = [
        "## Functional Tests (LLMock)",
        "",
        f"- Status: **{status}**",
        f"- Exit code: `{test_exit_code}`",
        f"- Tests: `{tests}`",
        f"- Failures: `{failures}`",
        f"- Errors: `{errors}`",
        f"- Skipped: `{skipped}`",
        "",
        "### Token Usage",
        "",
    ]

    if token_hits:
        lines.extend(
            [
                f"- Prompt tokens: `{token_totals['prompt_tokens']}`",
                f"- Completion tokens: `{token_totals['completion_tokens']}`",
                f"- Total tokens: `{token_totals['total_tokens']}`",
                f"- Usage events parsed: `{token_hits}`",
            ]
        )
    else:
        lines.append(
            "- No token usage fields found in LLMock logs "
            "(`prompt_tokens`, `completion_tokens`, `total_tokens`)."
        )

    if failed_testcases:
        lines.extend(["", "### Failed Testcases", ""])
        for test_name, detail in failed_testcases[:MAX_FAILURE_DETAILS]:
            lines.append(f"- `{test_name}`: {detail}")

    if troubleshooting_hints:
        lines.extend(["", "### Troubleshooting Hints", ""])
        for hint in troubleshooting_hints:
            lines.append(f"- {hint}")

    return "\n".join(lines) + "\n"


def main() -> int:
    """Publish the functional test summary to GitHub Actions step summary."""
    args = parse_args()
    exit_code = args.test_exit_code
    if exit_code is None:
        exit_code = int(os.environ.get("TEST_EXIT_CODE", "1"))

    junit_path = Path(args.junit_file)
    llmock_log_path = Path(args.llmock_log)
    tests_log_path = Path(args.tests_log)

    tests, failures, errors, skipped = parse_junit_totals(junit_path)
    token_totals, token_hits = parse_token_usage(llmock_log_path)
    failed_testcases = parse_failed_testcases(junit_path)
    troubleshooting_hints = detect_troubleshooting_hints(
        tests_log_path,
        llmock_log_path,
    )
    summary = build_summary(
        test_exit_code=exit_code,
        tests=tests,
        failures=failures,
        errors=errors,
        skipped=skipped,
        token_totals=token_totals,
        token_hits=token_hits,
        failed_testcases=failed_testcases,
        troubleshooting_hints=troubleshooting_hints,
    )

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
    with summary_path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(summary)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
