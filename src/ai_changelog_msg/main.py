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
    parse_conventional_commit,
    parse_note_metadata,
    parse_semantic_version,
)
from ai_changelog_msg.config import Config
from ai_changelog_msg.git_helper import GitRepository

logger = logging.getLogger(__name__)
RELEASE_SECTION_HEADING_RE = re.compile(r"^## \[[^\]]+\](?: - .*)?$", re.MULTILINE)


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
        "ai-changelog",
        repo_path,
        "--model",
        model,
        "--namespace",
        namespace,
    ]

    if force:
        args.append("--force")
    if clear_all:
        args.append("--clear-all")
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
        args.extend(["--litellm-api-base", litellm_api_base])
    if litellm_api_key:
        args.extend(["--litellm-api-key", "[REDACTED]"])
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
    if item_count <= 0:
        return 1

    if requested_workers is None:
        cpu_count = os.cpu_count() or 1
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
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )
    # Silence noisy third-party loggers unless debug is requested
    if level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("litellm").setLevel(logging.WARNING)
        litellm_logger = logging.getLogger("LiteLLM")
        litellm_logger.setLevel(logging.WARNING)
        # Prevent LiteLLM's own logger handlers from polluting CLI progress output.
        litellm_logger.handlers.clear()
        litellm_logger.propagate = False


def _render_worker_progress_bar(done: int, total: int, width: int = 20) -> str:
    """Return a fixed-width progress bar string for worker progress."""
    if total <= 0:
        completed = width
    else:
        completed = min(width, int((done / total) * width))
    return f"[{'#' * completed}{'-' * (width - completed)}]"


def _generate_summary_for_commit(
    ai_provider: AIProvider,
    prepared: _PreparedCommit,
) -> _SummaryResult:
    """Generate an AI summary for one commit and capture failures as data."""
    try:
        summary = ai_provider.summarize_diff(
            commit_message=prepared.commit_message,
            diff=prepared.diff,
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
        worker_id = index % workers
        assignments[prepared.commit.hexsha] = worker_id
        totals[worker_id] = totals.get(worker_id, 0) + 1
        completed.setdefault(worker_id, 0)

    interactive = bool(getattr(sys.stdout, "isatty", lambda: False)())

    def render_worker_lines() -> list[str]:
        lines = ["Per-worker summary progress:"]
        for worker_id in range(workers):
            total = totals.get(worker_id, 0)
            done = completed.get(worker_id, 0)
            bar = _render_worker_progress_bar(done, total)
            lines.append(f"  Worker {worker_id + 1:>2}: {bar} {done}/{total}")
        return lines

    last_line_count = 0

    def draw() -> None:
        nonlocal last_line_count
        lines = render_worker_lines()
        if interactive and last_line_count > 0:
            # Move cursor to previously rendered block start and clear line-by-line.
            click.echo(f"\x1b[{last_line_count}A", nl=False)
            for _ in range(last_line_count):
                click.echo("\r\x1b[2K", nl=False)
                click.echo("\x1b[1B", nl=False)
            click.echo(f"\x1b[{last_line_count}A", nl=False)

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
            worker_id = assignments[result.commit_hash]
            completed[worker_id] = completed.get(worker_id, 0) + 1
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
        return message.decode("utf-8", errors="replace")
    return str(message)


def _create_semver_tags_if_needed(
    repo: GitRepository,
    commits: Iterable[Any],
    namespace: str,
    create_semver_tags: bool,
    limit: int | None,
) -> int:
    """Create semantic-version tags for untagged repositories.

    Tags are inferred from git-note categories using semantic-version rules:
    ``Added`` -> minor, ``Fixed``/``Changed`` -> patch, and
    ``Removed`` -> major. Tags are created as lightweight ``vX.Y.Z`` tags.

    Creation only runs when explicitly requested and only if no semantic
    version tags already exist in the repository.

    Args:
        repo: Repository wrapper used to read existing tags and create new ones.
        commits: Commit iterable used as the release timeline.
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
    has_semver_tags = any(
        parse_semantic_version(tag_name) is not None
        for tag_names in tags_by_commit.values()
        for tag_name in tag_names
    )
    if has_semver_tags:
        click.echo(
            "Semantic version tags already exist; skipping automatic tag creation"
        )
        return 0

    ordered_commits = sorted(
        commits,
        key=lambda commit: (commit.committed_datetime, commit.hexsha),
    )
    current_version: SemanticVersion | None = None
    created = 0
    category_to_release_type = {
        "Removed": "major",
        "Added": "minor",
        "Fixed": "patch",
        "Changed": "patch",
    }

    for commit in ordered_commits:
        note = repo.get_note(commit.hexsha, namespace)
        category, _ = parse_note_metadata(note or "")
        if category is None:
            continue

        release_type = category_to_release_type.get(category)
        if release_type is None:
            continue

        if current_version is None:
            current_version = SemanticVersion(1, 0, 0)
        else:
            current_version = current_version.bump(release_type)

        tag_name = f"v{current_version}"
        if repo.create_tag(tag_name, commit.hexsha):
            created += 1

    if created > 0:
        click.echo(f"Created {created} semantic version tag(s)")
    else:
        click.echo("No release commits found; no semantic version tags created")
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
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(changelog_text)
        )
        heading = match.group(0).strip()
        block = changelog_text[start:end].strip("\n")
        sections.append((heading, block))
    return sections


def _merge_missing_release_sections(
    existing_text: str, generated_text: str
) -> tuple[str, int]:
    """Return regenerated changelog text when release sections differ.

    Existing release headings are treated as stable identities, but their
    content must still be refreshed when regenerated output changes. This keeps
    reruns idempotent while allowing stale or previously malformed entries to
    be corrected in place.

    Returns:
        Tuple of output text and number of release sections that changed.
    """
    existing_sections = dict(_extract_release_sections(existing_text))
    generated_sections = dict(_extract_release_sections(generated_text))

    changed_sections = [
        heading
        for heading, block in generated_sections.items()
        if existing_sections.get(heading) != block
    ]
    removed_sections = [
        heading for heading in existing_sections if heading not in generated_sections
    ]

    if (
        not changed_sections
        and not removed_sections
        and existing_text == generated_text
    ):
        return existing_text, 0

    return generated_text, len(changed_sections) + len(removed_sections)


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
    default="ai-changelog",
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
    "--litellm-api-base",
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

        ai_provider = AIProvider(config)
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

        prepared_commits: list[_PreparedCommit] = []
        summaries_to_generate: list[_PreparedCommit] = []

        with click.progressbar(
            commits, label="Preparing commits", show_pos=True
        ) as progress:
            for commit in progress:
                commit_message = _commit_message_str(commit.message)
                existing_note = repo.get_note(commit.hexsha, namespace)
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
                prepared_commits.append(prepared)
                if (not existing_note or force) and diff.strip():
                    summaries_to_generate.append(prepared)

        if not summaries_to_generate:
            click.echo(
                "No AI summaries to generate: all processable commits already have notes"
            )

        overall_total = _resolve_overall_progress_total(
            overall_progress_mode=overall_progress_mode,
            prepared_commits_count=len(prepared_commits),
            summaries_to_generate_count=len(summaries_to_generate),
        )
        click.echo(f"Overall progress mode: {overall_progress_mode}")
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

            processed = 0
            skipped = 0
            failed = 0

            with click.progressbar(
                prepared_commits, label="Processing commits", show_pos=True
            ) as progress:
                for prepared in progress:
                    commit = prepared.commit
                    try:
                        logger.debug("Checking commit %s", commit.hexsha[:8])
                        existing_note = prepared.existing_note
                        diff = prepared.diff
                        if not diff.strip():
                            logger.debug("Skipping %s — empty diff", commit.hexsha[:8])
                            click.echo(f"\nSkipping {commit.hexsha[:8]} (empty diff)")
                            skipped += 1
                            continue

                        category = prepared.category

                        if existing_note and not force:
                            existing_category, existing_summary = parse_note_metadata(
                                existing_note
                            )
                            if existing_category is not None:
                                logger.debug(
                                    "Skipping %s — note already exists",
                                    commit.hexsha[:8],
                                )
                                skipped += 1
                                continue
                            note_payload = format_note(
                                category=category,
                                summary=existing_summary or existing_note,
                            )
                            repo.set_note(commit.hexsha, note_payload, namespace)
                            logger.debug(
                                "Upgraded note format for %s", commit.hexsha[:8]
                            )
                            processed += 1
                            continue

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

                        note_payload = format_note(category=category, summary=summary)
                        repo.set_note(commit.hexsha, note_payload, namespace)
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
                        click.echo(f"\nError processing {commit.hexsha[:8]}: {error}")
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

        if processed == 0 and skipped > 0 and failed == 0:
            click.echo(
                "No notes were updated in this run; continuing with changelog "
                "finalization from existing notes"
            )

        click.echo("Finalizing release metadata and changelog...")

        with click.progressbar(
            length=3, label="Finalization", show_pos=True
        ) as progress:
            _create_semver_tags_if_needed(
                repo=repo,
                commits=commits,
                namespace=namespace,
                create_semver_tags=create_semver_tags,
                limit=limit,
            )
            progress.update(1)

            logger.debug("Rendering changelog using namespace '%s'", namespace)
            changelog_builder = ChangelogBuilder(namespace=namespace)
            changelog = changelog_builder.build(
                commits=commits,
                get_note=repo.get_note,
                tags_by_commit=repo.get_semantic_version_tags(),
                generate_entry=ai_provider.generate_changelog_entry,
                commit_url_for_hash=repo.get_commit_web_url,
                get_diff=repo.get_commit_diff,
            )
            progress.update(1)

            changelog_path = repo.resolve_output_path(changelog_file)
            changelog_path.parent.mkdir(parents=True, exist_ok=True)
            if changelog_path.exists():
                existing_text = changelog_path.read_text(encoding="utf-8")
                merged_text, appended_sections = _merge_missing_release_sections(
                    existing_text=existing_text,
                    generated_text=changelog,
                )
                if appended_sections > 0:
                    changelog_path.write_text(merged_text, encoding="utf-8")
                    click.echo(
                        f"Changelog updated with {appended_sections} changed release section(s): {changelog_path}"
                    )
                else:
                    click.echo(f"Changelog already up-to-date: {changelog_path}")
            else:
                changelog_path.write_text(changelog, encoding="utf-8")
                click.echo(f"Changelog written to: {changelog_path}")
            progress.update(1)

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
