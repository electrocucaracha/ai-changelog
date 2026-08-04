---
description: "Python development standards for this project: apply Python best practices, follow the Zen of Python, use typing, and always provide docstrings for modules, classes, and functions."
applyTo: "**/*.py"
---

# Python Development Guidelines

Follow the Zen of Python from `import this` when generating or editing Python code in this repository.
Target Python 3.9+ and keep code aligned with this project's `src/` layout, CLI usage, linting, and test conventions.

## Core Principles

- Prefer readability over cleverness.
- Keep implementations explicit and easy to follow.
- Choose simple solutions before introducing abstraction.
- Use descriptive names for modules, classes, functions, variables, and tests.
- Keep functions focused on a single responsibility.
- Match the existing project style and structure before introducing new patterns.

## Project Conventions

- Keep source code under `src/ai_changelog_msg` and tests under `tests`.
- Preserve the existing public API and CLI behavior unless the task requires a change.
- Follow the project's formatting and linting conventions: Black-style formatting, isort-compatible imports, Ruff-clean code, and 88 character line length.
- Prefer double quotes to match the existing formatter configuration.
- Reuse existing dependencies and patterns before introducing new packages or architectural layers.

## Typing And Signatures

- Add type hints to new public functions, methods, and important internal helpers.
- Prefer standard built-in generic types such as `list[str]`, `dict[str, str]`, and `tuple[int, str]`.
- Keep function signatures explicit; avoid ambiguous `Any` unless there is a real interoperability need.
- Return structured data with clear types instead of overloaded tuple conventions or loosely shaped dictionaries when a class or model is clearer.
- Keep parameter lists small and cohesive; group related configuration into existing models or objects when appropriate.

## Docstring Requirements

- Add a module docstring to every new Python module.
- Add docstrings to public classes, functions, and methods.
- Prefer docstrings for non-trivial internal helpers when the intent is not obvious from the code.
- Add or update docstrings when behavior changes.
- Write docstrings that describe purpose, important arguments, return values, raised exceptions, and side effects when relevant.
- Keep docstrings concise and practical; avoid repeating the function name or restating obvious code.

## Implementation Guidance

- Prefer standard library features unless a dependency is already justified by the project.
- Make error handling explicit and actionable.
- Raise specific exceptions with clear messages instead of broad or silent failures.
- Validate inputs at the boundary where invalid state first becomes detectable.
- Keep control flow shallow when possible; use guard clauses to reduce nesting.
- Avoid hidden side effects and surprising mutation.
- Favor small, testable units over dense inline logic.
- Prefer pure functions for transformation logic when practical.
- Isolate I/O, subprocess, network, and git interactions so they are easier to mock in tests.
- Preserve backwards-compatible behavior unless the task requires a change.
- Add brief comments only when intent would otherwise be unclear from the code and docstring.

## Imports And Module Design

- Group imports as standard library, third-party, then first-party.
- Avoid unused imports, wildcard imports, and circular dependencies.
- Keep modules focused; split files when they begin mixing unrelated responsibilities.
- Prefer explicit imports and clear names over aliasing that obscures meaning.

## Data Models And Configuration

- Prefer existing configuration and model patterns used in the repository.
- Use Pydantic models where the project already expects structured configuration or validated data.
- Centralize parsing and validation logic instead of scattering ad hoc conversions across call sites.
- Keep defaults explicit and safe.

## CLI And User-Facing Behavior

- Keep command-line behavior predictable and documented.
- Write user-facing messages that are concise and actionable.
- When changing CLI behavior, update help text, docs, and related tests together.

## Testing Guidance

- Keep tests readable and behavior-focused.
- Use pytest conventions already present in the repository.
- Use descriptive test names that explain the expected outcome.
- Prefer focused unit tests for changed logic before broader integration coverage.
- Mock external dependencies at the boundary rather than deep inside implementation details.
- Cover error paths and edge cases when behavior is changed.
- Cover changed logic with focused tests when practical.

## Documentation And Maintenance

- Update nearby documentation when behavior, configuration, or CLI usage changes.
- Remove dead code, stale branches, and obsolete comments as part of the change when they are directly related.
- Avoid speculative abstractions; introduce extension points only when the codebase already needs them.

## Docstring Example

```python
"""Utilities for building changelog entries."""


def summarize_commits(commits: list[str]) -> str:
    """Return a single summary string for a list of commit messages.

    Args:
        commits: Commit message strings in chronological order.

    Returns:
        A human-readable summary assembled from the provided commits.

    Raises:
        ValueError: If `commits` is empty.
    """
    if not commits:
        raise ValueError("commits cannot be empty")
    return "; ".join(commits)
```