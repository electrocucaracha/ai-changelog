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

"""Changelog management for AI Changelog Generator."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

SEMVER_TAG_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
)
CATEGORY_ORDER = ("Added", "Changed", "Fixed", "Removed")
NOTE_CATEGORY_RE = re.compile(
    r"^\s*Category\s*:\s*(Added|Changed|Fixed|Removed)\s*$", re.IGNORECASE
)
LEADING_WORD_RE = re.compile(r"^(?P<word>[A-Za-z][A-Za-z'-]*)(?P<rest>\b.*)$")
BREAKING_PREFIX_RE = re.compile(r"^(?P<prefix>BREAKING:\s+)(?P<rest>.*)$")

CATEGORY_POWER_VERBS: dict[str, tuple[str, ...]] = {
    "Added": (
        "Enabled",
        "Introduced",
        "Unlocked",
        "Delivered",
        "Expanded",
    ),
    "Changed": (
        "Refined",
        "Optimized",
        "Improved",
        "Modernized",
        "Updated",
        "Simplified",
        "Hardened",
    ),
    "Fixed": (
        "Resolved",
        "Corrected",
        "Repaired",
        "Addressed",
        "Eliminated",
        "Stabilized",
    ),
    "Removed": (
        "Removed",
        "Retired",
        "Eliminated",
        "Dropped",
    ),
}
POWER_VERB_SET = {
    verb.lower() for verbs in CATEGORY_POWER_VERBS.values() for verb in verbs
}


@dataclass(frozen=True, order=True)
class SemanticVersion:
    """Simple semantic version value object.

    Examples:
        >>> str(SemanticVersion(1, 2, 3))
        '1.2.3'
        >>> str(SemanticVersion(1, 2, 3).bump("patch"))
        '1.2.4'
        >>> str(SemanticVersion(1, 2, 3).bump("minor"))
        '1.3.0'
        >>> str(SemanticVersion(1, 2, 3).bump("major"))
        '2.0.0'
    """

    major: int
    minor: int
    patch: int

    def bump(self, release_type: str) -> SemanticVersion:
        """Return the next version for *release_type*."""
        if release_type == "major":
            return SemanticVersion(self.major + 1, 0, 0)
        if release_type == "minor":
            return SemanticVersion(self.major, self.minor + 1, 0)
        if release_type == "patch":
            return SemanticVersion(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unsupported release type: {release_type}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class ParsedCommit:
    """Parsed Conventional Commit metadata."""

    raw_message: str
    description: str
    commit_type: str | None
    scope: str | None
    is_breaking: bool
    release_type: str | None


@dataclass(frozen=True)
class ChangelogItem:
    """Normalised changelog entry sourced from a commit and its git note.

    When ``changelog_entry`` is provided, it is treated as a refined
    AI-generated sentence and preferred over ``note`` during rendering.
    """

    commit_hash: str
    committed_at: datetime
    category: str
    release_type: str | None
    note: str
    description: str
    is_breaking: bool
    changelog_entry: str | None = None
    commit_url: str | None = None

    @property
    def summary(self) -> str:
        """Return a concise, changelog-safe summary line.

        Examples:
            >>> note_text = "Added support for notes.\\n\\nThis expands the CLI."
            >>> item = ChangelogItem(
            ...     commit_hash="abc12345",
            ...     committed_at=datetime(2026, 3, 17),
            ...     category="Added",
            ...     release_type="minor",
            ...     note=note_text,
            ...     description="add notes support",
            ...     is_breaking=False,
            ... )
            >>> item.summary
            'Added support for notes.'
        """
        source_text = self.changelog_entry or self.note
        text = " ".join(
            line.strip() for line in source_text.splitlines() if line.strip()
        )
        if not text:
            text = self.description
        sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        if self.is_breaking and not sentence.lower().startswith("breaking"):
            sentence = f"BREAKING: {sentence}"
        return sentence


@dataclass(frozen=True)
class ReleaseSection:
    """Rendered changelog release section."""

    title: str
    date: str | None
    items: Sequence[ChangelogItem]
    predicted_release_type: str | None = None
    predicted_version: SemanticVersion | None = None


class ChangelogBuilder:
    """Build a Keep-a-Changelog style document from git notes and commits.

    The builder supports two versioning modes:
    - Tagged mode: uses existing semantic tags (``vX.Y.Z`` or ``X.Y.Z``).
    - Synthetic mode: infers release versions from conventional commits.

    Version inference follows semantic-release compatible rules: breaking
    changes produce a major bump, ``feat`` produces a minor bump, and
    ``fix``/``perf``/``revert`` produce a patch bump.
    """

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace

    def build(
        self,
        commits: Iterable[Any],
        get_note: Callable[[str, str], str | None],
        tags_by_commit: dict[str, list[str]] | None = None,
        generate_entry: Callable[[str, str, str, bool], str] | None = None,
        commit_url_for_hash: Callable[[str], str | None] | None = None,
        get_diff: Callable[[Any], str] | None = None,
    ) -> str:
        """Return a rendered ``CHANGELOG.md`` document.

        Args:
            commits: Commit iterable to transform into release entries.
            get_note: Function used to retrieve git note content by
                ``(commit_hash, namespace)``.
            tags_by_commit: Optional mapping of ``commit_hash`` to tag names.
                When semantic tags are present, tagged mode is used.
            generate_entry: Optional callback that refines note text into a
                one-line changelog sentence. Intended for AI-based postprocessing.
            commit_url_for_hash: Optional callback that returns a commit URL for
                a full commit SHA. When available, rendered entries include a
                clickable hash link.
            get_diff: Optional callback that returns unified diff text for a
                commit. When provided, added/removed line counts are used to
                improve category inference.
        """
        ordered_commits = sorted(
            commits,
            key=lambda commit: (commit.committed_datetime, commit.hexsha),
        )
        items = [
            self._build_item(
                commit,
                get_note,
                generate_entry,
                commit_url_for_hash,
                get_diff,
            )
            for commit in ordered_commits
        ]
        valid_tags = self._normalise_tags(tags_by_commit or {})
        sections = self._build_sections(items, valid_tags)
        return self._render(sections)

    def _build_item(
        self,
        commit: Any,
        get_note: Callable[[str, str], str | None],
        generate_entry: Callable[[str, str, str, bool], str] | None,
        commit_url_for_hash: Callable[[str], str | None] | None,
        get_diff: Callable[[Any], str] | None,
    ) -> ChangelogItem:
        parsed = parse_conventional_commit(commit.message)
        raw_note = get_note(commit.hexsha, self.namespace) or parsed.description
        note_category, note_summary = parse_note_metadata(raw_note)
        note = note_summary
        added_lines = 0  # pragma: no mutate
        removed_lines = 0  # pragma: no mutate
        if get_diff is not None:
            diff_text = get_diff(commit)
            added_lines, removed_lines = count_diff_lines(diff_text)
        category = note_category or infer_category(
            parsed.commit_type,
            parsed.description,
            parsed.is_breaking,  # pragma: no mutate
            added_lines=added_lines,
            removed_lines=removed_lines,
        )
        changelog_entry = None
        if generate_entry is not None:
            changelog_entry = generate_entry(
                commit.message,
                note,  # pragma: no mutate
                category,
                parsed.is_breaking,  # pragma: no mutate
            )
        commit_url = commit_url_for_hash(commit.hexsha) if commit_url_for_hash else None
        return ChangelogItem(
            commit_hash=commit.hexsha,
            committed_at=commit.committed_datetime,
            category=category,
            release_type=parsed.release_type,
            note=note,
            description=parsed.description,  # pragma: no mutate
            is_breaking=parsed.is_breaking,  # pragma: no mutate
            changelog_entry=changelog_entry,
            commit_url=commit_url,
        )

    def _normalise_tags(
        self, tags_by_commit: dict[str, list[str]]
    ) -> dict[str, SemanticVersion]:
        versions: dict[str, SemanticVersion] = {}
        for commit_hash, tag_names in tags_by_commit.items():
            all_parsed_versions = [
                parse_semantic_version(tag_name) for tag_name in tag_names
            ]
            parsed_versions: list[SemanticVersion] = [
                version for version in all_parsed_versions if version is not None
            ]
            if parsed_versions:
                versions[commit_hash] = max(parsed_versions)
        return versions

    def _build_sections(
        self,
        items: Sequence[ChangelogItem],
        tags_by_commit: dict[str, SemanticVersion],
    ) -> list[ReleaseSection]:
        if tags_by_commit:
            return self._build_sections_from_tags(items, tags_by_commit)
        return self._build_synthetic_sections(items)

    def _build_unreleased_section(
        self,
        bucket: list[ChangelogItem],
        latest_version: SemanticVersion | None,
    ) -> ReleaseSection:
        """Build the trailing ``Unreleased`` section common to both tag-based
        and synthetic release strategies.

        Args:
            bucket: Commits accumulated after the last tagged release.
            latest_version: The most recent tagged (or synthetic) version, used
                to predict what the next version will be.

        Returns:
            A :class:`ReleaseSection` with ``title="Unreleased"`` that includes
            the predicted next release type and version when they can be inferred.
        """
        predicted_release_type = highest_release_type(bucket)
        predicted_version = (
            latest_version.bump(predicted_release_type)
            if latest_version is not None and predicted_release_type is not None
            else None
        )
        return ReleaseSection(
            title="Unreleased",
            date=None,
            items=tuple(bucket),
            predicted_release_type=predicted_release_type,
            predicted_version=predicted_version,
        )

    def _build_sections_from_tags(
        self,
        items: Sequence[ChangelogItem],
        tags_by_commit: dict[str, SemanticVersion],
    ) -> list[ReleaseSection]:
        sections: list[ReleaseSection] = []
        bucket: list[ChangelogItem] = []
        latest_version: SemanticVersion | None = None  # pragma: no mutate

        for item in items:
            bucket.append(item)
            version = tags_by_commit.get(item.commit_hash)
            if version is None:
                continue
            latest_version = version
            sections.append(
                ReleaseSection(
                    title=str(version),
                    date=item.committed_at.date().isoformat(),
                    items=tuple(bucket),
                )
            )
            bucket = []

        unreleased = self._build_unreleased_section(bucket, latest_version)
        return [unreleased] + list(reversed(sections))

    def _build_synthetic_sections(
        self, items: Sequence[ChangelogItem]
    ) -> list[ReleaseSection]:
        sections: list[ReleaseSection] = []
        bucket: list[ChangelogItem] = []
        current_version: SemanticVersion | None = None

        for item in items:
            bucket.append(item)
            if item.release_type is None:
                continue
            if current_version is None:
                current_version = SemanticVersion(1, 0, 0)
            else:
                current_version = current_version.bump(item.release_type)
            sections.append(
                ReleaseSection(
                    title=str(current_version),
                    date=item.committed_at.date().isoformat(),
                    items=tuple(bucket),
                )
            )
            bucket = []

        unreleased = self._build_unreleased_section(
            bucket, current_version
        )  # pragma: no mutate
        return [unreleased] + list(reversed(sections))

    def _render(self, sections: Sequence[ReleaseSection]) -> str:
        parts = [
            "<!-- Markdownlint-disable MD024 -->",
            "",  # pragma: no mutate
            "# Changelog",
            "",  # pragma: no mutate
            "All notable changes to this project will be documented in this file.",  # pragma: no mutate
            "",  # pragma: no mutate
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),",  # pragma: no mutate
            (
                "and this project adheres to [Semantic Versioning]"
                "(https://semver.org/spec/v2.0.0.html)."
            ),  # pragma: no mutate
        ]

        for section in sections:
            parts.extend(["", self._render_heading(section), ""])  # pragma: no mutate
            if (
                section.title == "Unreleased" and section.predicted_version is not None
            ):  # pragma: no mutate
                parts.append(
                    f"Predicted next version: {section.predicted_version} ({section.predicted_release_type})"
                )
                parts.append("")  # pragma: no mutate
            category_blocks = self._group_items_by_category(section.items)
            if not category_blocks:
                continue
            for category in CATEGORY_ORDER:
                entries = category_blocks.get(category, [])  # pragma: no mutate
                if not entries:
                    continue
                parts.append(f"### {category}")
                seen_leading_verbs: set[str] = set()
                for entry in entries:
                    short_hash = entry.commit_hash[:8]
                    summary = self._diversify_leading_verb(
                        entry.summary,
                        category,
                        seen_leading_verbs,
                    )
                    if entry.commit_url:
                        parts.append(f"- {summary} [{short_hash}]({entry.commit_url})")
                    else:
                        parts.append(f"- {summary} ({short_hash})")
                parts.append("")  # pragma: no mutate
            if parts[-1] == "":  # pragma: no mutate
                parts.pop()

        return "\n".join(parts).rstrip() + "\n"  # pragma: no mutate

    def _render_heading(self, section: ReleaseSection) -> str:
        if section.date is None:
            return "## [Unreleased]"  # pragma: no mutate
        return f"## [{section.title}] - {section.date}"

    def _group_items_by_category(
        self,
        items: Sequence[ChangelogItem],
    ) -> dict[str, list[ChangelogItem]]:
        grouped: dict[str, list[ChangelogItem]] = {
            category: [] for category in CATEGORY_ORDER
        }
        for item in items:
            grouped.setdefault(item.category, []).append(item)  # pragma: no mutate
        return {category: entries for category, entries in grouped.items() if entries}

    def _diversify_leading_verb(
        self,
        summary: str,
        category: str,
        seen_leading_verbs: set[str],
    ) -> str:
        """Reduce repeated leading power verbs within a category block.

        Keeps the original sentence when no safe alternative is available.
        """
        text = summary.strip()
        if not text:
            return summary

        prefix = ""  # pragma: no mutate
        body = text
        breaking_match = BREAKING_PREFIX_RE.match(text)
        if breaking_match is not None:
            prefix = breaking_match.group("prefix")
            body = breaking_match.group("rest")

        word_match = LEADING_WORD_RE.match(body)
        if word_match is None:
            return summary

        leading_word = word_match.group("word")
        normalized = leading_word.lower()
        rest = word_match.group("rest")

        if normalized not in POWER_VERB_SET:
            return summary

        if normalized not in seen_leading_verbs:
            seen_leading_verbs.add(normalized)
            return summary

        alternatives = CATEGORY_POWER_VERBS.get(category, ())
        for alternative in alternatives:
            candidate = alternative.lower()
            if candidate in seen_leading_verbs:
                continue
            replacement = (
                alternative.upper()
                if leading_word.isupper()
                else (
                    alternative.lower() if leading_word.islower() else alternative
                )  # pragma: no mutate
            )
            seen_leading_verbs.add(candidate)  # pragma: no mutate
            return f"{prefix}{replacement}{rest}"

        return summary


def parse_semantic_version(tag_name: str) -> SemanticVersion | None:
    """Parse a tag name like ``v1.2.3`` into :class:`SemanticVersion`.

    Examples:
        >>> parse_semantic_version("v1.2.3")
        SemanticVersion(major=1, minor=2, patch=3)
        >>> parse_semantic_version("release-1.2.3") is None
        True
    """
    match = SEMVER_TAG_PATTERN.match(tag_name.strip())
    if match is None:
        return None
    return SemanticVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
    )


def parse_conventional_commit(message: str) -> ParsedCommit:
    """Parse a conventional-commit message and infer release metadata.

    Examples:
        >>> parse_conventional_commit("fix(parser): handle empty input").release_type
        'patch'
        >>> parse_conventional_commit("feat!: drop Python 3.8 support").release_type
        'major'
        >>> parse_conventional_commit("docs: refresh README").release_type is None
        True
    """
    raw_message = message.strip()
    subject = raw_message.splitlines()[0] if raw_message else ""
    match = CONVENTIONAL_COMMIT_PATTERN.match(subject)
    breaking_footer = (
        "BREAKING CHANGE:" in raw_message
        or "BREAKING CHANGES:" in raw_message  # pragma: no mutate
    )

    if match is None:
        description = subject or "Unclassified change"
        return ParsedCommit(
            raw_message=raw_message,
            description=description,
            commit_type=None,
            scope=None,
            is_breaking=breaking_footer,
            release_type="major" if breaking_footer else None,
        )

    commit_type = match.group("type")
    description = match.group("description")
    is_breaking = bool(match.group("breaking")) or breaking_footer
    release_type = infer_release_type(commit_type, is_breaking)
    return ParsedCommit(
        raw_message=raw_message,
        description=description,
        commit_type=commit_type,
        scope=match.group("scope"),
        is_breaking=is_breaking,
        release_type=release_type,
    )


def infer_release_type(commit_type: str | None, is_breaking: bool) -> str | None:
    """Map conventional-commit metadata to semantic-release bump types."""
    if is_breaking:
        return "major"
    if commit_type == "feat":
        return "minor"
    if commit_type in {"fix", "perf", "revert"}:
        return "patch"
    return None


def infer_category(
    commit_type: str | None,
    description: str,
    is_breaking: bool,
    added_lines: int = 0,  # pragma: no mutate
    removed_lines: int = 0,  # pragma: no mutate
) -> str:
    """Map commit metadata and diff stats to a Keep-a-Changelog category.

    Args:
        commit_type: Conventional commit type, if available.
        description: Conventional commit description text.
        is_breaking: Whether the commit is marked as breaking.
        added_lines: Number of added diff lines (excluding headers).
        removed_lines: Number of removed diff lines (excluding headers).
    """
    lower_description = description.lower()
    if any(
        word in lower_description
        for word in ("remove", "removed", "drop", "delete")  # pragma: no mutate
    ):
        return "Removed"
    if commit_type == "feat":
        return "Added"
    if commit_type in {"fix", "revert"}:  # pragma: no mutate
        return "Fixed"
    if (
        is_breaking and removed_lines > 0 and removed_lines >= added_lines
    ):  # pragma: no mutate
        return "Removed"
    if removed_lines > 0 and added_lines == 0:  # pragma: no mutate
        return "Removed"
    if added_lines > 0 and removed_lines == 0:
        return "Added"
    return "Changed"


def count_diff_lines(diff_text: str) -> tuple[int, int]:
    """Count added and removed lines in a unified diff.

    Diff metadata lines (``+++``, ``---``, and hunk headers) are excluded.
    """
    added_lines = 0  # pragma: no mutate
    removed_lines = 0  # pragma: no mutate
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---", "@@")):  # pragma: no mutate
            continue
        if line.startswith("+"):
            added_lines += 1
        elif line.startswith("-"):
            removed_lines += 1  # pragma: no mutate
    return added_lines, removed_lines


def format_note(category: str, summary: str) -> str:
    """Return a git-note payload with explicit changelog category metadata.

    Examples:
        >>> format_note("Added", "Added support for changelog generation.")
        'Category: Added\\n\\nAdded support for changelog generation.'
    """
    normalized_category = category.strip().title()
    if normalized_category not in CATEGORY_ORDER:
        raise ValueError(f"Unsupported category: {category}")
    cleaned_summary = summary.strip() or "No summary available."  # pragma: no mutate
    return f"Category: {normalized_category}\n\n{cleaned_summary}"


def parse_note_metadata(note_text: str) -> tuple[str | None, str]:
    """Extract optional category metadata and summary body from a git note.

    Supports notes written as:
    ``Category: <Added|Changed|Fixed|Removed>``
    followed by a blank line and free-form summary text.

    Returns:
        Tuple of ``(category_or_none, summary_text)``.
    """
    if not note_text:
        return None, ""  # pragma: no mutate

    lines = note_text.splitlines()
    if not lines:
        return None, ""  # pragma: no mutate

    category_match = NOTE_CATEGORY_RE.match(lines[0])
    if category_match is None:
        return None, note_text.strip()

    category = category_match.group(1).title()
    summary = "\n".join(lines[1:]).strip()  # pragma: no mutate
    return category, summary or "No summary available."  # pragma: no mutate


def highest_release_type(items: Sequence[ChangelogItem]) -> str | None:
    """Return the highest semantic-release bump required by *items*.

    Examples:
        >>> items = [
        ...     ChangelogItem("a", datetime(2026, 3, 17), "Changed", "patch", "", "", False),
        ...     ChangelogItem("b", datetime(2026, 3, 17), "Added", "minor", "", "", False),
        ... ]
        >>> highest_release_type(items)
        'minor'
    """
    priorities = {"patch": 1, "minor": 2, "major": 3}  # pragma: no mutate
    highest: str | None = None
    highest_priority = 0
    for item in items:
        if item.release_type is None:
            continue
        priority = priorities[item.release_type]
        if priority > highest_priority:  # pragma: no mutate
            highest = item.release_type
            highest_priority = priority
    return highest


def extract_versions_from_changelog(changelog_text: str) -> set[str]:
    """Extract all semantic version strings from existing changelog.

    Uses regex to find release section headings in the format ``## [X.Y.Z]``
    or ``## [vX.Y.Z]`` and returns the version tokens found inside brackets.

    Args:
        changelog_text: Markdown changelog content.

    Returns:
        Set of version strings (e.g. ``{"1.0.0", "1.1.0", "2.0.0"}``).
    """
    versions: set[str] = set()
    pattern = re.compile(r"^## \[(?:v)?([^\]]+)\]", re.MULTILINE)  # pragma: no mutate
    for match in pattern.finditer(changelog_text):
        version_str = match.group(1).strip()
        if parse_semantic_version(version_str) is not None:
            versions.add(version_str)
    return versions


def merge_changelogs_with_keepachangelog(
    existing_text: str,
    generated_text: str,
) -> tuple[str, int]:
    """Merge generated changelog into existing file, avoiding duplicate releases.

    This function uses keepachangelog-compatible logic to:
    1. Preserve existing release sections.
    2. Extract versions from both existing and generated changelogs.
    3. Only add new release sections that are strictly newer than the highest
       version already in the existing file (avoids back-filling old per-commit
       tags that were never tracked in the changelog).
    4. Maintain proper Keep a Changelog structure.

    Args:
        existing_text: Current changelog content (or empty string if new).
        generated_text: Newly generated changelog content.

    Returns:
        Tuple of (merged_text, number_of_sections_added).
    """
    if not existing_text.strip():
        return generated_text, 0

    existing_versions = extract_versions_from_changelog(existing_text)

    if not existing_versions:
        # No existing releases, prepend unreleased section from existing
        return _merge_with_no_existing_releases(existing_text, generated_text)

    # Determine the ceiling: only append versions strictly above the current max
    parsed_existing = [parse_semantic_version(v) for v in existing_versions]
    max_existing: SemanticVersion | None = max(  # pragma: no mutate
        (v for v in parsed_existing if v is not None),
        default=None,  # pragma: no mutate
    )

    # Extract only the new release sections from generated changelog
    generated_sections = _extract_release_sections_kac(generated_text)
    appended_sections = 0
    new_sections_text = ""  # pragma: no mutate

    for heading, block in generated_sections:
        version = _release_version_from_heading_kac(heading)
        if version is None or version in existing_versions:
            continue
        # Skip versions older than or equal to the highest existing version
        parsed_version = parse_semantic_version(version)
        if max_existing is not None and (
            parsed_version is None
            or parsed_version <= max_existing  # pragma: no mutate
        ):
            continue  # pragma: no mutate
        if not new_sections_text:
            new_sections_text = f"{heading}\n\n{block}"
        else:
            new_sections_text += f"\n\n{heading}\n\n{block}"
        appended_sections += 1

    if appended_sections == 0:
        return existing_text, 0

    # Find insertion point: after Unreleased section or at the end
    insertion_point = _find_insertion_point_kac(existing_text)
    merged = (
        existing_text[:insertion_point]
        + new_sections_text
        + "\n\n"  # pragma: no mutate
        + existing_text[insertion_point:]
    )

    return merged.strip() + "\n", appended_sections  # pragma: no mutate


def _merge_with_no_existing_releases(
    existing_text: str,
    generated_text: str,
) -> tuple[str, int]:
    """Merge when existing file has no release sections yet."""
    existing_sections = _extract_release_sections_kac(existing_text)
    generated_sections = _extract_release_sections_kac(generated_text)

    unreleased_blocks = [
        block for heading, block in existing_sections if _is_unreleased_heading(heading)
    ]

    # Collect all generated releases
    appended_sections = 0
    merged_parts = []

    # Add any existing unreleased content first
    if unreleased_blocks:
        merged_parts.append("## [Unreleased]\n")  # pragma: no mutate
        merged_parts.append(unreleased_blocks[0])

    # Add all generated release sections
    for heading, block in generated_sections:
        if not _is_unreleased_heading(heading):
            merged_parts.append(heading)
            merged_parts.append(block)
            appended_sections += 1

    if not merged_parts:
        return generated_text, 0

    result = "\n\n".join(merged_parts).strip() + "\n"  # pragma: no mutate
    return result, appended_sections


def _extract_release_sections_kac(changelog_text: str) -> list[tuple[str, str]]:
    """Extract release sections from Keep a Changelog markdown.

    Returns list of (heading, block) tuples where heading is the ## line
    and block is everything until the next ## heading or EOF.
    """
    sections: list[tuple[str, str]] = []
    pattern = re.compile(r"^(## \[[^\]]+\].*?)$", re.MULTILINE)
    matches = list(pattern.finditer(changelog_text))

    for idx, match in enumerate(matches):
        start = match.start()
        heading = match.group(1).strip()

        # Find content end (next heading or EOF)
        if idx + 1 < len(matches):  # pragma: no mutate
            end = matches[idx + 1].start()  # pragma: no mutate
        else:
            end = len(changelog_text)  # pragma: no mutate

        block = changelog_text[start + len(heading) : end].strip()
        sections.append((heading, block))

    return sections


def _release_version_from_heading_kac(heading: str) -> str | None:
    """Extract version from Keep a Changelog heading like ``## [1.2.3]``."""
    match = re.match(r"^## \[(?:v)?([^\]]+)\]", heading.strip())
    if match is None:
        return None
    version_str = match.group(1).strip()
    return version_str if parse_semantic_version(version_str) is not None else None


def _is_unreleased_heading(heading: str) -> bool:
    """Check if heading is an Unreleased section."""
    return heading.strip().lower() == "## [unreleased]"


def _find_insertion_point_kac(existing_text: str) -> int:
    """Find the position to insert new release sections.

    Returns the position right after the Unreleased section, or at the
    beginning of the first semantic release section if no Unreleased exists.
    """
    pattern = re.compile(r"^(## \[Unreleased\].*?)^(## \[)", re.MULTILINE | re.DOTALL)
    match = pattern.search(existing_text)

    if match:
        return match.end() - len("## [")  # Position just before next ## [

    # No Unreleased found, insert at beginning
    first_release = re.search(r"^## \[", existing_text, re.MULTILINE)
    if first_release:
        return first_release.start()

    # No releases at all, append at end
    return len(existing_text)
