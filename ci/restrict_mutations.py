#!/usr/bin/env python3
"""Restrict mutmut execution to a single module for CI matrix runs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for mutmut restriction."""
    parser = argparse.ArgumentParser(
        description="Update pyproject.toml so mutmut targets one module."
    )
    parser.add_argument(
        "--module",
        required=True,
        help="Module name under src/ai_changelog_msg (without .py).",
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml (default: pyproject.toml).",
    )
    return parser.parse_args()


def validate_module_name(module: str) -> None:
    """Ensure the provided module name is a safe Python module identifier."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", module):
        raise ValueError(
            "Invalid module name. Use lowercase letters, numbers, and underscores."
        )


def update_mutmut_target(pyproject_path: Path, module: str) -> str:
    """Set or insert `only_mutate` in the [tool.mutmut] section.

    Args:
        pyproject_path: Path to pyproject.toml.
        module: Module name without .py extension.

    Returns:
        The mutation target path that was written.

    Raises:
        FileNotFoundError: If pyproject.toml or the module file does not exist.
        RuntimeError: If the [tool.mutmut] section cannot be located.
    """
    if not pyproject_path.exists():
        raise FileNotFoundError(f"Could not find {pyproject_path}")

    target_path = f"src/ai_changelog_msg/{module}.py"
    if not Path(target_path).exists():
        raise FileNotFoundError(f"Could not find target module file: {target_path}")

    replacement = f'only_mutate = ["{target_path}"]'
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    pyproject_text, replacement_count = re.subn(
        r"only_mutate\s*=\s*\[[^\]]*\]",
        replacement,
        pyproject_text,
        count=1,
    )

    if replacement_count == 0:
        pyproject_text, section_count = re.subn(
            r"(\[tool\.mutmut\]\n)",
            r"\1" + replacement + "\n",
            pyproject_text,
            count=1,
        )
        if section_count != 1:
            raise RuntimeError("Could not locate [tool.mutmut] in pyproject.toml")
        print("No existing only_mutate entry found; inserted one into [tool.mutmut].")
    else:
        print("Replaced existing only_mutate entry in [tool.mutmut].")

    pyproject_path.write_text(pyproject_text, encoding="utf-8")
    return target_path


def print_mutmut_section(pyproject_path: Path) -> None:
    """Print the effective [tool.mutmut] section for troubleshooting."""
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^\[tool\.mutmut\]\n(.*?)(?=^\[|\Z)", text)
    if not match:
        print("WARNING: [tool.mutmut] section not found after update.")
        return

    print("Effective [tool.mutmut] section:")
    print("[tool.mutmut]")
    print(match.group(1).rstrip())


def main() -> int:
    """Run the CLI entrypoint."""
    args = parse_args()
    try:
        validate_module_name(args.module)
        pyproject_path = Path(args.pyproject)
        target_path = update_mutmut_target(pyproject_path, args.module)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Mutmut restricted to: {target_path}")
    print_mutmut_section(Path(args.pyproject))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
