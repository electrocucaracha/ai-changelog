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

import logging
import re
import sys
from typing import Any, Iterable, Optional

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
    limit: Optional[int],
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
        list(commits),
        key=lambda commit: (commit.committed_datetime, commit.hexsha),
    )
    current_version: Optional[SemanticVersion] = None
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
    """Append only release sections missing from *existing_text*.

    Existing section content is never modified; only absent sections from the
    newly generated changelog are appended to the end of the file.

    Returns:
        Tuple of merged text and number of appended sections.
    """
    existing_headings = set(RELEASE_SECTION_HEADING_RE.findall(existing_text))
    missing_blocks = [
        block
        for heading, block in _extract_release_sections(generated_text)
        if heading not in existing_headings
    ]
    if not missing_blocks:
        return existing_text, 0

    merged_text = (
        existing_text.rstrip("\n") + "\n\n" + "\n\n".join(missing_blocks) + "\n"
    )
    return merged_text, len(missing_blocks)


@click.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "--model",
    default="ollama/llama3.1",
    help="AI model to use for summaries (default: ollama/llama3.1)",
)
@click.option(
    "--namespace",
    default="ai-changelog",
    help="Git notes namespace (default: ai-changelog)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-generate summaries for commits that already have notes",
)
@click.option(
    "--clear-all",
    is_flag=True,
    help="Remove all git notes in the selected namespace and exit",
)
@click.option(
    "--create-semver-tags",
    is_flag=True,
    help="Create semantic version tags when the repository has no semantic tags",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Process only the last N commits",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level (default: INFO)",
    show_default=True,
)
@click.option(
    "--changelog-file",
    default="CHANGELOG.md",
    help="Write a changelog file into the target repository after note generation",
    show_default=True,
)
def cli(
    repo_path: str,
    model: str,
    namespace: str,
    force: bool,
    clear_all: bool,
    create_semver_tags: bool,
    limit: Optional[int],
    log_level: str,
    changelog_file: str,
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
        logger.debug(
            "Initialising configuration: model=%s namespace=%s", model, namespace
        )
        config = Config(model=model, namespace=namespace)

        logger.debug("Opening repository at %s", repo_path)
        repo = GitRepository(repo_path)
        click.echo(f"Repository: {repo.repo_path}")

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

        click.echo(f"Found {total_commits} commits to process")

        processed = 0
        skipped = 0
        failed = 0

        with click.progressbar(
            commits, label="Processing commits", show_pos=True
        ) as progress:
            for commit in progress:
                try:
                    logger.debug("Checking commit %s", commit.hexsha[:8])
                    existing_note = repo.get_note(commit.hexsha, namespace)
                    diff = repo.get_commit_diff(commit)
                    if not diff.strip():
                        logger.debug("Skipping %s — empty diff", commit.hexsha[:8])
                        click.echo(f"\nSkipping {commit.hexsha[:8]} (empty diff)")
                        skipped += 1
                        continue

                    parsed = parse_conventional_commit(
                        _commit_message_str(commit.message)
                    )
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

                    if existing_note and not force:
                        existing_category, existing_summary = parse_note_metadata(
                            existing_note
                        )
                        if existing_category is not None:
                            logger.debug(
                                "Skipping %s — note already exists", commit.hexsha[:8]
                            )
                            skipped += 1
                            continue
                        note_payload = format_note(
                            category=category,
                            summary=existing_summary or existing_note,
                        )
                        repo.set_note(commit.hexsha, note_payload, namespace)
                        logger.debug("Upgraded note format for %s", commit.hexsha[:8])
                        processed += 1
                        continue

                    logger.debug("Generating summary for %s", commit.hexsha[:8])
                    summary = ai_provider.summarize_diff(
                        commit_message=_commit_message_str(commit.message),
                        diff=diff,
                        author=commit.author.name if commit.author else "Unknown",
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

        click.echo("\nProcessing complete")
        click.echo(f"   Processed: {processed}")
        click.echo(f"   Skipped:   {skipped}")
        click.echo(f"   Failed:    {failed}")
        logger.info(
            "Done — processed=%d skipped=%d failed=%d", processed, skipped, failed
        )

        _create_semver_tags_if_needed(
            repo=repo,
            commits=commits,
            namespace=namespace,
            create_semver_tags=create_semver_tags,
            limit=limit,
        )

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
                    f"Changelog updated with {appended_sections} missing release section(s): {changelog_path}"
                )
            else:
                click.echo(f"Changelog already up-to-date: {changelog_path}")
        else:
            changelog_path.write_text(changelog, encoding="utf-8")
            click.echo(f"Changelog written to: {changelog_path}")

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
