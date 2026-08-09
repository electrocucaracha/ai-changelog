# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main CLI entry point for AI Changelog Generator."""

# pylint: disable=too-many-lines
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import sys
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import click

from ai_changelog_msg.ai_provider import AIProvider
from ai_changelog_msg.changelog import (
    ChangelogBuilder,
    SemanticVersion,
    count_diff_lines,
    format_note,
    infer_category,
    merge_changelogs_with_keepachangelog,
    parse_conventional_commit,
    parse_note_metadata,
    parse_semantic_version,
)
from ai_changelog_msg.config import Config
from ai_changelog_msg.git_helper import GitRepository

logger = logging.getLogger(__name__)
RELEASE_SECTION_HEADING_RE = re.compile(r"^## \[[^\]]+\](?: - .*)?$", re.MULTILINE)
MARKDOWNLINT_MD024_DISABLE = "<!-- Markdownlint-disable MD024 -->"


@dataclass(frozen=True)
class _PreparedCommit:
    """Prepared commit payload for processing in the CLI workflow."""

    commit: Any
    commit_message: str
    category: str
    existing_note: str | None
    diff: str


@dataclass(frozen=True)
class _SummaryResult:
    """Result from a single AI summary generation task."""

    commit_hash: str
    summary: str | None = None
    error: Exception | None = None


# jscpd:ignore-start
def _build_execution_command(
    repo_path: str,
    model: str,
    namespace: str,
    force: bool,
    clear_all: bool,
    create_semver_tags: bool,
    limit: int | None,
    log_level: str,
    changelog_file: str,
    litellm_api_base: str | None,
    litellm_api_key: str | None,
    litellm_headers_json: str | None,
    workers: int | None = None,
    retry_attempts: int | None = None,
    retry_backoff_seconds: float | None = None,
    overall_progress_mode: str | None = None,
) -> str:  # jscpd:ignore-end
    """Build a shell-safe command summary of the current CLI execution.

    Sensitive values are not emitted directly.
    """
    args: list[str] = [
        "ai-changelog",  # pragma: no mutate
        repo_path,
        "--model",
        model,
        "--namespace",
        namespace,
    ]

    if force:
        args.append("--force")  # pragma: no mutate
    if clear_all:
        args.append("--clear-all")  # pragma: no mutate
    if create_semver_tags:
        args.append("--create-semver-tags")
    if limit is not None:
        args.extend(["--limit", str(limit)])
    if workers is not None:
        args.extend(["--workers", str(workers)])
    if retry_attempts is not None:
        args.extend(["--retry-attempts", str(retry_attempts)])
    if retry_backoff_seconds is not None:
        args.extend(["--retry-backoff-seconds", str(retry_backoff_seconds)])
    if overall_progress_mode is not None:
        args.extend(["--overall-progress-mode", overall_progress_mode])

    args.extend(["--log-level", log_level, "--changelog-file", changelog_file])

    if litellm_api_base:
        args.extend(["--litellm-api-base", litellm_api_base])  # pragma: no mutate
    if litellm_api_key:
        args.extend(["--litellm-api-key", "[REDACTED]"])  # pragma: no mutate
    if litellm_headers_json:
        args.extend(["--litellm-headers-json", "$CHANGELOG_LITELLM_HEADERS_JSON"])

    return " ".join(shlex.quote(part) for part in args)


def _resolve_worker_count(requested_workers: int | None, item_count: int) -> int:
    """Resolve worker count using request, CPU availability, and item count.

    Args:
        requested_workers: Explicit worker override from CLI, or ``None`` to
            auto-size from ``os.cpu_count()``.
        item_count: Number of items that could be processed.

    Returns:
        A positive worker count bounded by ``item_count``.
    """
    if item_count <= 0:  # pragma: no mutate
        return 1

    if requested_workers is None:
        cpu_count = os.cpu_count() or 1  # pragma: no mutate
        return max(1, min(cpu_count, item_count))

    return max(1, min(requested_workers, item_count))


def _resolve_overall_progress_total(
    overall_progress_mode: str,
    prepared_commits_count: int,
    summaries_to_generate_count: int,
) -> int:
    """Return total units for the selected overall progress mode."""
    if overall_progress_mode == "work-units":
        return prepared_commits_count + summaries_to_generate_count
    return prepared_commits_count


def _configure_logging(log_level: str) -> None:
    """Configure the root logger for the application.

    Applies a timestamped ``stderr`` handler to the root logger and silences
    verbose third-party loggers (``httpx``, ``httpcore``, ``litellm``, and
    ``LiteLLM``) when *log_level* is above ``DEBUG``. For LiteLLM specifically,
    existing handlers are cleared and propagation is disabled to avoid progress
    bar corruption in CLI output.

    Args:
        log_level: Case-insensitive level name recognised by :mod:`logging`,
            e.g. ``"INFO"`` or ``"DEBUG"``.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)  # pragma: no mutate
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # pragma: no mutate
        datefmt="%Y-%m-%dT%H:%M:%S",  # pragma: no mutate
        level=level,  # pragma: no mutate
        stream=sys.stderr,  # pragma: no mutate
    )
    # Silence noisy third-party loggers unless debug is requested
    if level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)  # pragma: no mutate
        logging.getLogger("litellm").setLevel(logging.WARNING)
        litellm_logger = logging.getLogger("LiteLLM")  # pragma: no mutate
        litellm_logger.setLevel(logging.WARNING)
        # Prevent LiteLLM's own logger handlers from polluting CLI progress output.
        litellm_logger.handlers.clear()
        litellm_logger.propagate = False  # pragma: no mutate


def _render_worker_progress_bar(
    done: int, total: int, width: int = 20
) -> str:  # pragma: no mutate
    """Return a fixed-width progress bar string for worker progress."""
    if total <= 0:
        completed = width
    else:
        completed = min(width, int((done / total) * width))  # pragma: no mutate
    return f"[{'#' * completed}{'-' * (width - completed)}]"


def _generate_summary_for_commit(
    ai_provider: AIProvider,
    prepared: _PreparedCommit,
) -> _SummaryResult:
    """Generate an AI summary for one commit and capture failures as data."""
    try:
        summary = ai_provider.summarize_diff(
            commit_message=prepared.commit_message,
            diff=prepared.diff,  # pragma: no mutate
            author=(
                prepared.commit.author.name
                if getattr(prepared.commit, "author", None)
                else None
            ),
        )
    except Exception as error:  # noqa: BLE001
        return _SummaryResult(commit_hash=prepared.commit.hexsha, error=error)

    return _SummaryResult(commit_hash=prepared.commit.hexsha, summary=summary)


def _generate_summaries_concurrently(
    ai_provider: AIProvider,
    prepared_commits: list[_PreparedCommit],
    workers: int,
    on_summary_completed: Callable[[], None] | None = None,
) -> dict[str, _SummaryResult]:
    """Generate AI summaries concurrently with per-worker progress output."""
    if not prepared_commits:
        return {}

    assignments: dict[str, int] = {}
    totals: dict[int, int] = {}
    completed: dict[int, int] = {}
    for index, prepared in enumerate(prepared_commits):
        worker_id = index % workers  # pragma: no mutate
        assignments[prepared.commit.hexsha] = worker_id
        totals[worker_id] = totals.get(worker_id, 0) + 1  # pragma: no mutate
        completed.setdefault(worker_id, 0)  # pragma: no mutate

    interactive = bool(
        getattr(sys.stdout, "isatty", lambda: False)()  # pragma: no mutate
    )  # pragma: no mutate

    def render_worker_lines() -> list[str]:
        lines = ["Per-worker summary progress:"]  # pragma: no mutate
        for worker_id in range(workers):
            total = totals.get(worker_id, 0)  # pragma: no mutate
            done = completed.get(worker_id, 0)  # pragma: no mutate
            progress_bar = _render_worker_progress_bar(done, total)
            lines.append(f"  Worker {worker_id + 1:>2}: {progress_bar} {done}/{total}")
        return lines

    last_line_count = 0  # pragma: no mutate

    def draw() -> None:
        nonlocal last_line_count
        lines = render_worker_lines()
        if interactive and last_line_count > 0:  # pragma: no mutate
            # Move cursor to previously rendered block start and clear line-by-line.
            click.echo(f"\x1b[{last_line_count}A", nl=False)  # pragma: no mutate
            for _ in range(last_line_count):
                click.echo("\r\x1b[2K", nl=False)  # pragma: no mutate
                click.echo("\x1b[1B", nl=False)  # pragma: no mutate
            click.echo(f"\x1b[{last_line_count}A", nl=False)  # pragma: no mutate

        for line in lines:
            click.echo(line)

        last_line_count = len(lines)

    draw()

    results: dict[str, _SummaryResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_generate_summary_for_commit, ai_provider, prepared)
            for prepared in prepared_commits
        ]
        for future in as_completed(futures):
            result = future.result()
            results[result.commit_hash] = result
            worker_id = assignments[result.commit_hash]  # pragma: no mutate
            completed[worker_id] = completed.get(worker_id, 0) + 1  # pragma: no mutate
            if on_summary_completed is not None:
                on_summary_completed()
            draw()

    if interactive:
        click.echo()

    return results


def _commit_message_str(message: Any) -> str:
    """Return *message* as a plain string, decoding bytes if necessary.

    GitPython may expose ``commit.message`` as either ``str`` or ``bytes``
    depending on the repository encoding. This helper normalises both cases
    so callers always receive a ``str``.

    Args:
        message: A value from ``Commit.message``; either ``str`` or ``bytes``.

    Returns:
        The message text as a ``str``.
    """
    if isinstance(message, bytes):
        return message.decode("utf-8", errors="replace")  # pragma: no mutate
    return str(message)


def _create_semver_tags_if_needed(
    repo: GitRepository,
    commits: Iterable[Any],
    namespace: str,
    create_semver_tags: bool,
    limit: int | None,
) -> int:
    """Create semantic-version tags for untagged noted commits.

    Tags are inferred from git-note categories using semantic-version rules:
    ``Added`` -> minor, ``Fixed``/``Changed`` -> patch, and
    ``Removed`` -> major. Tags are created as lightweight ``vX.Y.Z`` tags.

    Creation only runs when explicitly requested. If semantic tags already exist,
    the highest existing tag is used as the baseline and only commits without a
    tag receive a new tag. Commits that already have a semantic tag are skipped.

    Args:
        repo: Repository wrapper used to read existing tags and create new ones.
        commits: Commit iterable used as the release timeline.
        namespace: Git notes namespace for reading categories.
        create_semver_tags: Enables this feature when ``True``.
        limit: Commit limit from the CLI. Tag creation is blocked when set to
            avoid partial or incorrect version history.

    Returns the number of tags created.

    Raises:
        ValueError: If ``create_semver_tags`` is enabled together with
            ``--limit``.
    """
    if not create_semver_tags:
        return 0

    if limit is not None:
        raise ValueError("--create-semver-tags cannot be used with --limit")

    tags_by_commit = repo.get_semantic_version_tags()

    # Build set of commits that already have a semantic version tag
    tagged_commits: set[str] = set()
    highest_version: SemanticVersion | None = None
    for commit_hash, tag_names in tags_by_commit.items():
        for tag_name in tag_names:
            parsed = parse_semantic_version(tag_name)
            if parsed is not None:
                tagged_commits.add(commit_hash)
                if (
                    highest_version is None
                    or parsed > highest_version  # pragma: no mutate
                ):
                    highest_version = parsed

    ordered_commits = sorted(
        commits,
        key=lambda commit: (commit.committed_datetime, commit.hexsha),
    )
    current_version: SemanticVersion | None = highest_version
    created = 0
    category_to_release_type = {
        "Removed": "major",  # pragma: no mutate
        "Added": "minor",
        "Fixed": "patch",
        "Changed": "patch",
    }

    for commit in ordered_commits:
        # Skip commits that already have a semantic version tag
        if commit.hexsha in tagged_commits:
            continue  # pragma: no mutate

        note = repo.get_note(commit.hexsha, namespace)  # pragma: no mutate
        category, _ = parse_note_metadata(note or "")  # pragma: no mutate
        if category is None:
            continue  # pragma: no mutate

        release_type = category_to_release_type.get(category)
        if release_type is None:
            continue  # pragma: no mutate

        if current_version is None:
            current_version = SemanticVersion(1, 0, 0)
        else:
            current_version = current_version.bump(release_type)

        tag_name = f"v{current_version}"
        if repo.create_tag(tag_name, commit.hexsha):
            created += 1

    if created > 0:  # pragma: no mutate
        click.echo(f"Created {created} semantic version tag(s)")  # pragma: no mutate
    else:
        click.echo(
            "No new untagged release commits found; no new tags created"  # pragma: no mutate
        )
    return created


def _extract_release_sections(changelog_text: str) -> list[tuple[str, str]]:
    """Extract release sections from changelog markdown.

    A release section starts at a level-2 heading in the format
    ``## [Version]`` or ``## [Version] - YYYY-MM-DD`` and ends before the next
    matching release heading.
    """
    sections: list[tuple[str, str]] = []
    matches = list(RELEASE_SECTION_HEADING_RE.finditer(changelog_text))
    for index, match in enumerate(matches):
        start = match.start()
        end = (
            matches[index + 1].start()  # pragma: no mutate
            if index + 1 < len(matches)
            else len(changelog_text)
        )
        heading = match.group(0).strip()
        block = changelog_text[start:end].strip("\n")  # pragma: no mutate
        sections.append((heading, block))
    return sections


def _release_version_from_heading(heading: str) -> str | None:
    """Extract the release version token from a level-2 release heading.

    Supports headings such as ``## [1.2.3]`` and
    ``## [1.2.3] - YYYY-MM-DD``.

    Args:
        heading: Raw heading line for a release section.

    Returns:
        Version token found inside square brackets, or ``None`` when the
        heading does not follow the expected format.
    """
    match = re.match(r"^## \[([^\]]+)\]", heading.strip())
    if match is None:
        return None
    return match.group(1).strip()


def _normalize_release_sections(existing_text: str) -> str:
    """Normalize release section ordering and remove duplicate versions.

    Rules:
    1. Semantic-version release sections must appear after ``## [Unreleased]``.
    2. Duplicate semantic versions are removed, keeping the first occurrence.
    """
    matches = list(RELEASE_SECTION_HEADING_RE.finditer(existing_text))
    if not matches:
        return existing_text

    prefix = existing_text[: matches[0].start()]
    sections = _extract_release_sections(existing_text)

    unreleased_index: int | None = None
    for index, (heading, _) in enumerate(sections):
        version = _release_version_from_heading(heading)
        if version is not None and version.lower() == "unreleased":
            unreleased_index = index
            break

    if unreleased_index is not None:
        before = sections[:unreleased_index]
        unreleased = sections[unreleased_index]
        after = sections[unreleased_index + 1 :]

        semantic_before = [
            section
            for section in before
            if _is_semantic_release_heading(section[0])  # pragma: no mutate
        ]
        non_semantic_before = [
            section
            for section in before
            if not _is_semantic_release_heading(section[0])  # pragma: no mutate
        ]
        ordered = non_semantic_before + [unreleased] + semantic_before + after
    else:
        ordered = sections

    seen_versions: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for heading, block in ordered:
        version = _release_version_from_heading(heading)
        if (
            version is not None and parse_semantic_version(version) is not None
        ):  # pragma: no mutate
            if version in seen_versions:
                continue  # pragma: no mutate
            seen_versions.add(version)
        deduped.append((heading, block))

    rebuilt_sections = "\n\n".join(
        block.rstrip("\n") for _, block in deduped  # pragma: no mutate
    ).rstrip(  # pragma: no mutate
        "\n"  # pragma: no mutate
    )
    normalized_prefix = prefix.rstrip("\n")  # pragma: no mutate
    if normalized_prefix and rebuilt_sections:  # pragma: no mutate
        return f"{normalized_prefix}\n\n{rebuilt_sections}\n"
    if rebuilt_sections:
        return f"{rebuilt_sections}\n"
    return normalized_prefix + ("\n" if normalized_prefix else "")  # pragma: no mutate


def _is_semantic_release_heading(heading: str) -> bool:
    """Return ``True`` when *heading* contains a semantic version token."""
    version = _release_version_from_heading(heading)
    if version is None:
        return False  # pragma: no mutate
    return parse_semantic_version(version) is not None


def _ensure_unreleased_and_get_insertion_index(existing_text: str) -> tuple[str, int]:
    """Ensure an ``## [Unreleased]`` section exists and return insertion index.

    New semantic release sections are always inserted immediately after the
    full ``## [Unreleased]`` section.
    """
    matches = list(RELEASE_SECTION_HEADING_RE.finditer(existing_text))
    if not matches:
        base_text = existing_text.rstrip("\n")  # pragma: no mutate
        if base_text:
            updated = f"{base_text}\n\n## [Unreleased]\n\n"  # pragma: no mutate
        else:
            updated = "## [Unreleased]\n\n"  # pragma: no mutate
        return updated, len(updated)

    for index, match in enumerate(matches):
        heading = match.group(0).strip()
        version = _release_version_from_heading(heading)
        if version is not None and version.lower() == "unreleased":
            return existing_text, (
                matches[index + 1].start()  # pragma: no mutate
                if index + 1 < len(matches)  # pragma: no mutate
                else len(existing_text)
            )

    # If no Unreleased heading exists, insert one before the first semantic
    # release heading so future release sections always appear after it.
    for match in matches:
        if _is_semantic_release_heading(match.group(0).strip()):
            insertion_anchor = match.start()
            prefix = existing_text[:insertion_anchor].rstrip("\n")  # pragma: no mutate
            suffix = existing_text[insertion_anchor:].lstrip("\n")  # pragma: no mutate
            separator = "\n\n" if prefix else ""  # pragma: no mutate
            unreleased_block = "## [Unreleased]\n\n"
            updated = f"{prefix}{separator}{unreleased_block}{suffix}"
            insertion_index = len(f"{prefix}{separator}{unreleased_block}")
            return updated, insertion_index

    # Non-semantic headings exist but none are release headings.
    base_text = existing_text.rstrip("\n")  # pragma: no mutate
    if base_text:
        updated = f"{base_text}\n\n## [Unreleased]\n\n"  # pragma: no mutate
    else:
        updated = "## [Unreleased]\n\n"  # pragma: no mutate
    return updated, len(updated)


def _merge_missing_release_sections(
    existing_text: str, generated_text: str
) -> tuple[str, int]:
    """Append only release sections that do not yet exist.

    Existing release sections are never rewritten so previously generated
    content remains untouched. New sections are inserted immediately after
    ``## [Unreleased]`` when present, otherwise before the first semantic
    release heading.

    Returns:
        Tuple of output text and number of sections appended.
    """
    existing_text = _normalize_release_sections(existing_text)
    existing_text, insertion_index = _ensure_unreleased_and_get_insertion_index(
        existing_text
    )
    existing_sections = _extract_release_sections(existing_text)
    generated_sections = _extract_release_sections(generated_text)

    if not generated_sections:
        return existing_text, 0  # pragma: no mutate

    existing_versions = {
        version
        for heading, _ in existing_sections
        for version in [_release_version_from_heading(heading)]
        if version is not None
        and parse_semantic_version(version) is not None  # pragma: no mutate
    }
    parsed_existing = [parse_semantic_version(v) for v in existing_versions]
    max_existing = max(
        (v for v in parsed_existing if v is not None), default=None
    )  # pragma: no mutate

    missing_blocks = [
        block
        for heading, block in generated_sections
        for version in [_release_version_from_heading(heading)]
        for parsed_version in [
            parse_semantic_version(version) if version is not None else None
        ]
        if parsed_version is not None and version not in existing_versions
        # Only add versions strictly newer than the current highest version
        and (max_existing is None or parsed_version > max_existing)  # pragma: no mutate
    ]

    if not missing_blocks:
        return existing_text, 0  # pragma: no mutate

    insert_block = (
        "\n\n".join(missing_blocks).rstrip("\n") + "\n\n"  # pragma: no mutate
    )

    merged_text = (
        existing_text[:insertion_index] + insert_block + existing_text[insertion_index:]
    )
    return merged_text, len(missing_blocks)


def _ensure_markdownlint_md024_disable(changelog_text: str) -> tuple[str, bool]:
    """Ensure the changelog starts with an MD024 markdownlint disable marker.

    Returns:
        Tuple of ``(possibly_updated_text, was_inserted)``.
    """
    if MARKDOWNLINT_MD024_DISABLE in changelog_text:
        return changelog_text, False
    stripped_text = changelog_text.lstrip("\n")  # pragma: no mutate
    if not stripped_text:
        return f"{MARKDOWNLINT_MD024_DISABLE}\n", True  # pragma: no mutate
    return f"{MARKDOWNLINT_MD024_DISABLE}\n\n{stripped_text}", True


@click.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "--model",
    default="auto",
    envvar="CHANGELOG_MODEL",
    help=(
        "AI model to use for summaries. Use 'auto' to select a platform-aware "
        "default (Apple Silicon: ollama/llama3.1:8b-instruct-q4_K_M)."
    ),
)
@click.option(
    "--namespace",
    default="ai-changelog",  # pragma: no mutate
    envvar="CHANGELOG_NAMESPACE",
    help="Git notes namespace (default: ai-changelog)",
)
@click.option(
    "--force",
    is_flag=True,
    envvar="CHANGELOG_FORCE",
    help="Re-generate summaries for commits that already have notes",
)
@click.option(
    "--clear-all",
    is_flag=True,
    envvar="CHANGELOG_CLEAR_ALL",
    help="Remove all git notes in the selected namespace and exit",
)
@click.option(
    "--create-semver-tags",
    is_flag=True,
    envvar="CHANGELOG_CREATE_SEMVER_TAGS",
    help="Create semantic version tags when the repository has no semantic tags",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    envvar="CHANGELOG_LIMIT",
    help="Process only the last N commits",
)
@click.option(
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    envvar="CHANGELOG_WORKERS",
    help="Optional worker count hint for future parallel processing.",
)
@click.option(
    "--retry-attempts",
    type=click.IntRange(min=1),
    default=None,
    envvar="CHANGELOG_RETRY_ATTEMPTS",
    help="Max retry attempts for transient model/API failures.",
)
@click.option(
    "--retry-backoff-seconds",
    type=click.FloatRange(min=0.001),
    default=None,
    envvar="CHANGELOG_RETRY_BACKOFF_SECONDS",
    help="Base backoff delay in seconds between retry attempts.",
)
@click.option(
    "--overall-progress-mode",
    type=click.Choice(["commits", "work-units"], case_sensitive=False),
    default="commits",
    envvar="CHANGELOG_OVERALL_PROGRESS_MODE",
    help=(
        "Overall progress counting mode: 'commits' counts each commit once, "
        "'work-units' counts summary generation and commit processing separately."
    ),
    show_default=True,
)
@click.option(
    "--log-level",
    default="INFO",
    envvar="CHANGELOG_LOG_LEVEL",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level (default: INFO)",
    show_default=True,
)
@click.option(
    "--changelog-file",
    default="CHANGELOG.md",
    envvar="CHANGELOG_CHANGELOG_FILE",
    help="Write a changelog file into the target repository after note generation",
    show_default=True,
)
@click.option(
    "--litellm-api-base",  # pragma: no mutate
    default=None,
    help=(
        "Optional LiteLLM API base URL override for this run. "
        "Prefer provider-native env vars such as OPENAI_BASE_URL or "
        "AZURE_API_BASE."
    ),
)
@click.option(
    "--litellm-api-key",
    default=None,
    help=(
        "Optional LiteLLM API key override for this run. "
        "Prefer provider-native env vars such as OPENAI_API_KEY, "
        "ANTHROPIC_API_KEY, GEMINI_API_KEY, or LITELLM_PROXY_API_KEY."
    ),
)
@click.option(
    "--litellm-headers-json",
    default=None,
    envvar="CHANGELOG_LITELLM_HEADERS_JSON",
    help="Optional JSON object with extra headers for LiteLLM requests",
)
def cli(
    repo_path: str,
    model: str,
    namespace: str,
    force: bool,
    clear_all: bool,
    create_semver_tags: bool,
    limit: int | None,
    workers: int | None,
    retry_attempts: int | None,
    retry_backoff_seconds: float | None,
    overall_progress_mode: str,
    log_level: str,
    changelog_file: str,
    litellm_api_base: str | None,
    litellm_api_key: str | None,
    litellm_headers_json: str | None,
) -> None:
    """Generate AI git notes and an associated changelog for a repository.

    Operational modes:
    - Normal mode: process commits, generate/update notes, and write changelog.
    - ``--clear-all``: delete all notes under the selected namespace and exit.
        - ``--create-semver-tags``: when no semantic tags exist, infer and create
            ``vX.Y.Z`` tags from git-note categories before changelog rendering.
    """
    _configure_logging(log_level)
    try:
        litellm_extra_headers: dict[str, str] | None = None
        if litellm_headers_json:
            try:
                raw_headers = json.loads(litellm_headers_json)
            except json.JSONDecodeError as error:
                raise ValueError("--litellm-headers-json must be valid JSON") from error

            if not isinstance(raw_headers, dict):
                raise ValueError("--litellm-headers-json must be a JSON object")

            litellm_extra_headers = {}
            for key, value in raw_headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise TypeError(
                        "--litellm-headers-json must contain string keys and values"
                    )
                litellm_extra_headers[key] = value

        logger.debug(
            "Initialising configuration: model=%s namespace=%s", model, namespace
        )
        config_overrides: dict[str, Any] = {
            "model": model,
            "namespace": namespace,
            "litellm_api_base": litellm_api_base,
            "litellm_api_key": litellm_api_key,
            "litellm_extra_headers": litellm_extra_headers,
        }
        if retry_attempts is not None:
            config_overrides["retry_attempts"] = retry_attempts
        if retry_backoff_seconds is not None:
            config_overrides["retry_backoff_seconds"] = retry_backoff_seconds
        config = Config.from_env(**config_overrides)

        logger.debug("Opening repository at %s", repo_path)
        repo = GitRepository(repo_path)
        click.echo(f"Repository: {repo.repo_path}")
        click.echo(
            "Execution command: "
            + _build_execution_command(
                repo_path=repo_path,
                model=config.model,
                namespace=namespace,
                force=force,
                clear_all=clear_all,
                create_semver_tags=create_semver_tags,
                limit=limit,
                log_level=log_level,
                changelog_file=changelog_file,
                litellm_api_base=litellm_api_base,
                litellm_api_key=litellm_api_key,
                litellm_headers_json=litellm_headers_json,
                workers=workers,
                retry_attempts=retry_attempts,
                retry_backoff_seconds=retry_backoff_seconds,
                overall_progress_mode=overall_progress_mode,
            )
        )

        if clear_all:
            logger.info("Clearing all git notes in namespace '%s'", namespace)
            cleared = repo.clear_notes(namespace)
            if cleared:
                click.echo(f"Removed all git notes from namespace: {namespace}")
            else:
                click.echo(f"No git notes found for namespace: {namespace}")
            return

        ai_provider: AIProvider | None = None
        commits = repo.get_all_commits(limit=limit)
        total_commits = len(commits)
        logger.debug("Retrieved %d commits (limit=%s)", total_commits, limit)

        if total_commits == 0:
            logger.warning("No commits found in repository")
            click.echo("No commits found in repository")
            return

        effective_workers = _resolve_worker_count(workers, total_commits)
        logger.debug(
            "Resolved worker count: requested=%s effective=%s",
            workers,
            effective_workers,
        )

        click.echo(f"Found {total_commits} commits to process")
        if workers is None:
            click.echo(
                "Using "
                f"{effective_workers} worker(s) "
                f"(auto-selected from {os.cpu_count() or 1} CPU core(s))"
            )
        else:
            click.echo(f"Using {effective_workers} worker(s) (from --workers)")

        actionable_commits: list[_PreparedCommit] = []
        summaries_to_generate: list[_PreparedCommit] = []
        already_noted_count = 0
        empty_diff_count = 0
        note_cache: dict[str, str | None] = {}

        with click.progressbar(
            commits, label="Preparing commits", show_pos=True
        ) as prepare_progress:
            for commit in prepare_progress:
                commit_message = _commit_message_str(commit.message)
                existing_note = repo.get_note(commit.hexsha, namespace)
                note_cache[commit.hexsha] = existing_note

                # Fast path for no-op runs: when a commit already has a note and
                # regeneration is not forced, skip diff hydration entirely.
                if existing_note and not force:
                    already_noted_count += 1
                    continue

                diff = repo.get_commit_diff(commit)

                parsed = parse_conventional_commit(commit_message)
                added_lines, removed_lines = (0, 0)
                if diff and not diff.startswith("[Error retrieving diff:"):
                    added_lines, removed_lines = count_diff_lines(diff)
                category = infer_category(
                    parsed.commit_type,
                    parsed.description,
                    parsed.is_breaking,
                    added_lines=added_lines,
                    removed_lines=removed_lines,
                )

                prepared = _PreparedCommit(
                    commit=commit,
                    commit_message=commit_message,
                    category=category,
                    existing_note=existing_note,
                    diff=diff,
                )

                if not diff.strip():
                    empty_diff_count += 1
                    continue

                actionable_commits.append(prepared)
                if not existing_note or force:
                    summaries_to_generate.append(prepared)

        click.echo(
            "Commit classification: "
            f"actionable={len(actionable_commits)}, "
            f"already-noted={already_noted_count}, "
            f"empty-diff={empty_diff_count}"
        )

        if not summaries_to_generate:
            click.echo(
                "No AI summaries to generate: all processable commits already have notes"
            )

        overall_total = _resolve_overall_progress_total(
            overall_progress_mode=overall_progress_mode,
            prepared_commits_count=len(actionable_commits),
            summaries_to_generate_count=len(summaries_to_generate),
        )
        click.echo(f"Overall progress mode: {overall_progress_mode}")
        processed = 0
        skipped = 0
        failed = 0

        if overall_total == 0:
            summary_results: dict[str, _SummaryResult] = {}
            click.echo(
                "No commit processing needed: all commits already have categorized "
                "notes or empty diffs"
            )
        else:
            if ai_provider is None:
                ai_provider = AIProvider(config)
            with click.progressbar(
                length=overall_total,
                label="Overall progress",
                show_pos=True,
            ) as overall_progress:
                summary_results = _generate_summaries_concurrently(
                    ai_provider=ai_provider,
                    prepared_commits=summaries_to_generate,
                    workers=effective_workers,
                    on_summary_completed=(
                        (lambda: overall_progress.update(1))
                        if overall_progress_mode == "work-units"
                        else None
                    ),
                )

                with click.progressbar(
                    actionable_commits, label="Processing commits", show_pos=True
                ) as process_progress:
                    for prepared in process_progress:
                        commit = prepared.commit
                        try:
                            logger.debug("Checking commit %s", commit.hexsha[:8])
                            category = prepared.category

                            logger.debug(
                                "Reading generated summary for %s", commit.hexsha[:8]
                            )
                            summary_result = summary_results.get(commit.hexsha)
                            if summary_result is None:
                                raise RuntimeError(
                                    f"No summary result generated for {commit.hexsha[:8]}"
                                )
                            if summary_result.error is not None:
                                raise summary_result.error
                            summary = summary_result.summary
                            if summary is None:
                                raise RuntimeError(
                                    f"Summary result is empty for {commit.hexsha[:8]}"
                                )

                            note_payload = format_note(
                                category=category, summary=summary
                            )
                            repo.set_note(commit.hexsha, note_payload, namespace)
                            note_cache[commit.hexsha] = note_payload
                            # Keep per-commit status at DEBUG so the progress bar output
                            # remains readable at default INFO log level.
                            logger.debug("Stored note for %s", commit.hexsha[:8])
                            processed += 1
                        except Exception as error:
                            logger.error(
                                "Failed to process %s: %s",
                                commit.hexsha[:8],
                                error,
                                exc_info=logger.isEnabledFor(logging.DEBUG),
                            )
                            click.echo(
                                f"\nError processing {commit.hexsha[:8]}: {error}"
                            )
                            failed += 1
                        finally:
                            overall_progress.update(1)

        click.echo("\nProcessing complete")
        click.echo(f"   Processed: {processed}")
        click.echo(f"   Skipped:   {skipped}")
        click.echo(f"   Failed:    {failed}")
        logger.info(
            "Done — processed=%d skipped=%d failed=%d", processed, skipped, failed
        )

        if processed == 0 and failed == 0:
            click.echo(
                "No notes were updated in this run; continuing with changelog "
                "finalization from existing notes"
            )

        # When no notes changed, avoid per-commit AI rewrites and diff hydration.
        # This keeps finalization fast while preserving deterministic output.
        use_fast_finalization = processed == 0 and failed == 0

        click.echo("Finalizing release metadata and changelog...")

        with click.progressbar(
            length=3, label="Finalization", show_pos=True
        ) as final_progress:
            _create_semver_tags_if_needed(
                repo=repo,
                commits=commits,
                namespace=namespace,
                create_semver_tags=create_semver_tags,
                limit=limit,
            )
            final_progress.update(1)

            logger.debug("Rendering changelog using namespace '%s'", namespace)
            changelog_builder = ChangelogBuilder(namespace=namespace)
            if not use_fast_finalization and ai_provider is None:
                ai_provider = AIProvider(config)

            def get_note_cached(commit_hash: str, note_namespace: str) -> str | None:
                if commit_hash in note_cache:
                    return note_cache[commit_hash]
                note_value = repo.get_note(commit_hash, note_namespace)
                note_cache[commit_hash] = note_value
                return note_value

            changelog = changelog_builder.build(
                commits=commits,
                get_note=get_note_cached,
                tags_by_commit=repo.get_semantic_version_tags(),
                generate_entry=(
                    None
                    if use_fast_finalization
                    else (
                        ai_provider.generate_changelog_entry
                        if ai_provider is not None
                        else None
                    )
                ),
                commit_url_for_hash=repo.get_commit_web_url,
                get_diff=None if use_fast_finalization else repo.get_commit_diff,
            )
            final_progress.update(1)

            changelog_path = repo.resolve_output_path(changelog_file)
            changelog_path.parent.mkdir(parents=True, exist_ok=True)
            if changelog_path.exists():
                existing_text = changelog_path.read_text(encoding="utf-8")
                merged_text, appended_sections = merge_changelogs_with_keepachangelog(
                    existing_text=existing_text,
                    generated_text=changelog,
                )
                final_text, _added_md024_guard = _ensure_markdownlint_md024_disable(
                    merged_text
                )
                if final_text != existing_text:
                    changelog_path.write_text(final_text, encoding="utf-8")
                    click.echo(
                        f"Changelog updated with {appended_sections} appended release section(s): {changelog_path}"
                    )
                else:
                    click.echo(f"Changelog already up-to-date: {changelog_path}")
            else:
                final_text, _ = _ensure_markdownlint_md024_disable(changelog)
                changelog_path.write_text(final_text, encoding="utf-8")
                click.echo(f"Changelog written to: {changelog_path}")
            final_progress.update(1)

        if processed > 0:
            click.echo(
                f"\nView notes with: git notes --ref={namespace} show <commit-hash>"
            )
    except Exception as error:
        logger.critical("Fatal error: %s", error, exc_info=True)
        click.echo(f"Fatal error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
