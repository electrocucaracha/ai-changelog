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
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

SEMVER_TAG_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
)
CATEGORY_ORDER = ("Added", "Changed", "Fixed", "Removed")
NOTE_CATEGORY_RE = re.compile(
    r"^\s*Category\s*:\s*(Added|Changed|Fixed|Removed)\s*$", re.IGNORECASE
)


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

    def bump(self, release_type: str) -> "SemanticVersion":
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
    commit_type: Optional[str]
    scope: Optional[str]
    is_breaking: bool
    release_type: Optional[str]


@dataclass(frozen=True)
class ChangelogItem:
    """Normalised changelog entry sourced from a commit and its git note.

    When ``changelog_entry`` is provided, it is treated as a refined
    AI-generated sentence and preferred over ``note`` during rendering.
    """

    commit_hash: str
    committed_at: datetime
    category: str
    release_type: Optional[str]
    note: str
    description: str
    is_breaking: bool
    changelog_entry: Optional[str] = None
    commit_url: Optional[str] = None

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
        if len(sentence) > 180:
            sentence = sentence[:177].rstrip() + "..."
        if self.is_breaking and not sentence.lower().startswith("breaking"):
            sentence = f"BREAKING: {sentence}"
        return sentence


@dataclass(frozen=True)
class ReleaseSection:
    """Rendered changelog release section."""

    title: str
    date: Optional[str]
    items: Sequence[ChangelogItem]
    predicted_release_type: Optional[str] = None
    predicted_version: Optional[SemanticVersion] = None


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
        commits: Iterable[object],
        get_note: Callable[[str, str], Optional[str]],
        tags_by_commit: Optional[Dict[str, List[str]]] = None,
        generate_entry: Optional[Callable[[str, str, str, bool], str]] = None,
        commit_url_for_hash: Optional[Callable[[str], Optional[str]]] = None,
        get_diff: Optional[Callable[[object], str]] = None,
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
            list(commits),
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
        commit: object,
        get_note: Callable[[str, str], Optional[str]],
        generate_entry: Optional[Callable[[str, str, str, bool], str]],
        commit_url_for_hash: Optional[Callable[[str], Optional[str]]],
        get_diff: Optional[Callable[[object], str]],
    ) -> ChangelogItem:
        parsed = parse_conventional_commit(commit.message)
        raw_note = get_note(commit.hexsha, self.namespace) or parsed.description
        note_category, note_summary = parse_note_metadata(raw_note)
        note = note_summary
        added_lines = 0
        removed_lines = 0
        if get_diff is not None:
            diff_text = get_diff(commit)
            added_lines, removed_lines = count_diff_lines(diff_text)
        category = note_category or infer_category(
            parsed.commit_type,
            parsed.description,
            parsed.is_breaking,
            added_lines=added_lines,
            removed_lines=removed_lines,
        )
        changelog_entry = None
        if generate_entry is not None:
            changelog_entry = generate_entry(
                commit.message,
                note,
                category,
                parsed.is_breaking,
            )
        commit_url = commit_url_for_hash(commit.hexsha) if commit_url_for_hash else None
        return ChangelogItem(
            commit_hash=commit.hexsha,
            committed_at=commit.committed_datetime,
            category=category,
            release_type=parsed.release_type,
            note=note,
            description=parsed.description,
            is_breaking=parsed.is_breaking,
            changelog_entry=changelog_entry,
            commit_url=commit_url,
        )

    def _normalise_tags(
        self, tags_by_commit: Dict[str, List[str]]
    ) -> Dict[str, SemanticVersion]:
        versions: Dict[str, SemanticVersion] = {}
        for commit_hash, tag_names in tags_by_commit.items():
            parsed_versions = [
                parse_semantic_version(tag_name) for tag_name in tag_names
            ]
            parsed_versions = [
                version for version in parsed_versions if version is not None
            ]
            if parsed_versions:
                versions[commit_hash] = max(parsed_versions)
        return versions

    def _build_sections(
        self,
        items: Sequence[ChangelogItem],
        tags_by_commit: Dict[str, SemanticVersion],
    ) -> List[ReleaseSection]:
        if tags_by_commit:
            return self._build_sections_from_tags(items, tags_by_commit)
        return self._build_synthetic_sections(items)

    def _build_sections_from_tags(
        self,
        items: Sequence[ChangelogItem],
        tags_by_commit: Dict[str, SemanticVersion],
    ) -> List[ReleaseSection]:
        sections: List[ReleaseSection] = []
        bucket: List[ChangelogItem] = []
        latest_version: Optional[SemanticVersion] = None

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

        predicted_release_type = highest_release_type(bucket)
        predicted_version = (
            latest_version.bump(predicted_release_type)
            if latest_version is not None and predicted_release_type is not None
            else None
        )
        unreleased = ReleaseSection(
            title="Unreleased",
            date=None,
            items=tuple(bucket),
            predicted_release_type=predicted_release_type,
            predicted_version=predicted_version,
        )
        return [unreleased] + list(reversed(sections))

    def _build_synthetic_sections(
        self, items: Sequence[ChangelogItem]
    ) -> List[ReleaseSection]:
        sections: List[ReleaseSection] = []
        bucket: List[ChangelogItem] = []
        current_version: Optional[SemanticVersion] = None

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

        predicted_release_type = highest_release_type(bucket)
        predicted_version = (
            current_version.bump(predicted_release_type)
            if current_version is not None and predicted_release_type is not None
            else None
        )
        unreleased = ReleaseSection(
            title="Unreleased",
            date=None,
            items=tuple(bucket),
            predicted_release_type=predicted_release_type,
            predicted_version=predicted_version,
        )
        return [unreleased] + list(reversed(sections))

    def _render(self, sections: Sequence[ReleaseSection]) -> str:
        parts = [
            "# Changelog",
            "",
            "All notable changes to this project will be documented in this file.",
            "",
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),",
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).",
        ]

        for section in sections:
            parts.extend(["", self._render_heading(section), ""])
            if section.title == "Unreleased" and section.predicted_version is not None:
                parts.append(
                    f"Predicted next version: {section.predicted_version} ({section.predicted_release_type})"
                )
                parts.append("")
            category_blocks = self._group_items_by_category(section.items)
            if not category_blocks:
                continue
            for category in CATEGORY_ORDER:
                entries = category_blocks.get(category, [])
                if not entries:
                    continue
                parts.append(f"### {category}")
                for entry in entries:
                    short_hash = entry.commit_hash[:8]
                    if entry.commit_url:
                        parts.append(
                            f"- {entry.summary} [{short_hash}]({entry.commit_url})"
                        )
                    else:
                        parts.append(f"- {entry.summary} ({short_hash})")
                parts.append("")
            if parts[-1] == "":
                parts.pop()

        return "\n".join(parts).rstrip() + "\n"

    def _render_heading(self, section: ReleaseSection) -> str:
        if section.date is None:
            return "## [Unreleased]"
        return f"## [{section.title}] - {section.date}"

    def _group_items_by_category(
        self,
        items: Sequence[ChangelogItem],
    ) -> Dict[str, List[ChangelogItem]]:
        grouped: Dict[str, List[ChangelogItem]] = {
            category: [] for category in CATEGORY_ORDER
        }
        for item in items:
            grouped.setdefault(item.category, []).append(item)
        return {category: entries for category, entries in grouped.items() if entries}


def parse_semantic_version(tag_name: str) -> Optional[SemanticVersion]:
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
        "BREAKING CHANGE:" in raw_message or "BREAKING CHANGES:" in raw_message
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


def infer_release_type(commit_type: Optional[str], is_breaking: bool) -> Optional[str]:
    """Map conventional-commit metadata to semantic-release bump types."""
    if is_breaking:
        return "major"
    if commit_type == "feat":
        return "minor"
    if commit_type in {"fix", "perf", "revert"}:
        return "patch"
    return None


def infer_category(
    commit_type: Optional[str],
    description: str,
    is_breaking: bool,
    added_lines: int = 0,
    removed_lines: int = 0,
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
        word in lower_description for word in ("remove", "removed", "drop", "delete")
    ):
        return "Removed"
    if commit_type == "feat":
        return "Added"
    if commit_type in {"fix", "revert"}:
        return "Fixed"
    if is_breaking and removed_lines > 0 and removed_lines >= added_lines:
        return "Removed"
    if removed_lines > 0 and added_lines == 0:
        return "Removed"
    if added_lines > 0 and removed_lines == 0:
        return "Added"
    return "Changed"


def count_diff_lines(diff_text: str) -> Tuple[int, int]:
    """Count added and removed lines in a unified diff.

    Diff metadata lines (``+++``, ``---``, and hunk headers) are excluded.
    """
    added_lines = 0
    removed_lines = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added_lines += 1
        elif line.startswith("-"):
            removed_lines += 1
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
    cleaned_summary = summary.strip() or "No summary available."
    return f"Category: {normalized_category}\n\n{cleaned_summary}"


def parse_note_metadata(note_text: str) -> Tuple[Optional[str], str]:
    """Extract optional category metadata and summary body from a git note.

    Supports notes written as:
    ``Category: <Added|Changed|Fixed|Removed>``
    followed by a blank line and free-form summary text.

    Returns:
        Tuple of ``(category_or_none, summary_text)``.
    """
    if not note_text:
        return None, ""

    lines = note_text.splitlines()
    if not lines:
        return None, ""

    category_match = NOTE_CATEGORY_RE.match(lines[0])
    if category_match is None:
        return None, note_text.strip()

    category = category_match.group(1).title()
    summary = "\n".join(lines[1:]).strip()
    return category, summary or "No summary available."


def highest_release_type(items: Sequence[ChangelogItem]) -> Optional[str]:
    """Return the highest semantic-release bump required by *items*.

    Examples:
        >>> items = [
        ...     ChangelogItem("a", datetime(2026, 3, 17), "Changed", "patch", "", "", False),
        ...     ChangelogItem("b", datetime(2026, 3, 17), "Added", "minor", "", "", False),
        ... ]
        >>> highest_release_type(items)
        'minor'
    """
    priorities = {"patch": 1, "minor": 2, "major": 3}
    highest: Optional[str] = None
    highest_priority = 0
    for item in items:
        if item.release_type is None:
            continue
        priority = priorities[item.release_type]
        if priority > highest_priority:
            highest = item.release_type
            highest_priority = priority
    return highest
