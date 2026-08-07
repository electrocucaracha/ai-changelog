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

from datetime import UTC, datetime
from types import SimpleNamespace

from ai_changelog_msg.changelog import (
    ChangelogBuilder,
    _extract_release_sections_kac,
    _find_insertion_point_kac,
    _is_unreleased_heading,
    _release_version_from_heading_kac,
    format_note,
    infer_release_type,
    merge_changelogs_with_keepachangelog,
    parse_conventional_commit,
    parse_note_metadata,
)


def make_commit(hexsha: str, message: str, committed_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        hexsha=hexsha,
        message=message,
        committed_datetime=committed_at,
    )


def test_parse_conventional_commit_release_types():
    assert (
        parse_conventional_commit("fix(parser): handle blank input").release_type
        == "patch"
    )
    assert (
        parse_conventional_commit("feat(ui): add changelog output").release_type
        == "minor"
    )
    assert (
        parse_conventional_commit("feat!: remove deprecated CLI").release_type
        == "major"
    )
    assert parse_conventional_commit("docs: refresh readme").release_type is None


def test_build_synthetic_changelog_without_tags():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "11111111",
            "docs: document usage",
            datetime(2026, 3, 10, tzinfo=UTC),
        ),
        make_commit(
            "22222222",
            "feat(cli): generate changelog",
            datetime(2026, 3, 11, tzinfo=UTC),
        ),
        make_commit(
            "33333333",
            "fix(notes): handle empty note",
            datetime(2026, 3, 12, tzinfo=UTC),
        ),
    ]
    notes = {
        "11111111": "Documented the command line workflow.",
        "22222222": "Added automatic CHANGELOG.md generation after note creation.",
        "33333333": "Fixed empty-note handling while building release entries.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    assert "<!-- Markdownlint-disable MD024 -->" in changelog
    assert "## [1.0.1] - 2026-03-12" in changelog
    assert "## [1.0.0] - 2026-03-11" in changelog
    assert "### Added" in changelog
    assert "### Fixed" in changelog
    assert (
        "Added automatic CHANGELOG.md generation after note creation. (22222222)"
        in changelog
    )


def test_build_changelog_with_semver_tags_and_predicted_next_version():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "aaaaaaa1",
            "feat: initial public release",
            datetime(2026, 3, 1, tzinfo=UTC),
        ),
        make_commit(
            "bbbbbbb2",
            "fix: patch release bug",
            datetime(2026, 3, 2, tzinfo=UTC),
        ),
        make_commit(
            "ccccccc3",
            "feat(api): add comparison mode",
            datetime(2026, 3, 3, tzinfo=UTC),
        ),
    ]
    notes = {
        "aaaaaaa1": "Initial release with AI-generated git note summaries.",
        "bbbbbbb2": "Patched a regression in git note writing.",
        "ccccccc3": "Added comparison mode for release notes.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={
            "aaaaaaa1": ["v1.0.0"],
            "bbbbbbb2": ["v1.0.1"],
        },
    )

    assert "## [1.0.1] - 2026-03-02" in changelog
    assert "## [1.0.0] - 2026-03-01" in changelog
    assert "## [Unreleased]" in changelog
    assert "Predicted next version: 1.1.0 (minor)" in changelog
    assert "Added comparison mode for release notes. (ccccccc3)" in changelog


def test_build_changelog_prefers_ai_generated_entries():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "ddddddd4",
            "fix(cli): handle missing namespace",
            datetime(2026, 3, 4, tzinfo=UTC),
        )
    ]
    notes = {
        "ddddddd4": "Fixed an issue in namespace handling with additional internal details.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
        generate_entry=lambda commit_message, note, category, is_breaking: (
            "Fixed CLI namespace handling when notes are missing."
        ),
    )

    assert (
        "Fixed CLI namespace handling when notes are missing. (ddddddd4)" in changelog
    )


def test_build_changelog_renders_commit_markdown_links_when_available():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "eeeeeee5fffffff6789012345678901234567890",
            "feat(api): expose governance headers",
            datetime(2026, 3, 5, tzinfo=UTC),
        )
    ]
    notes = {
        "eeeeeee5fffffff6789012345678901234567890": (
            "Improved governance API interactions by adding new CLI flags"
            " to forward custom HTTP headers for more flexible requests."
        ),
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
        commit_url_for_hash=lambda commit_hash: (
            f"https://gecgithub01.walmart.com/v0m078y/metaregistry-catalog-checkers/commit/{commit_hash}"
        ),
    )

    assert (
        "Improved governance API interactions by adding new CLI flags"
        " to forward custom HTTP headers for more flexible requests. "
        "[eeeeeee5](https://gecgithub01.walmart.com/v0m078y/metaregistry-catalog-checkers/commit/"
        "eeeeeee5fffffff6789012345678901234567890)"
    ) in changelog


def test_build_changelog_uses_diff_line_counts_for_category():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "fffffff6",
            "chore: cleanup legacy paths",
            datetime(2026, 3, 6, tzinfo=UTC),
        )
    ]
    notes = {
        "fffffff6": "Removed obsolete compatibility paths from the project.",
    }
    removal_heavy_diff = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,4 +0,0 @@\n-line one\n-line two\n-line three"

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
        get_diff=lambda commit: removal_heavy_diff,
    )

    assert "### Removed" in changelog


def test_build_changelog_does_not_truncate_last_word_mid_sentence():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "ab12cd34",
            "feat: improve sentence handling",
            datetime(2026, 3, 7, tzinfo=UTC),
        )
    ]
    note_summary = "Enabled " + "resilience " * 40 + "behavior."
    notes = {
        "ab12cd34": f"Category: Added\n\n{note_summary}",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    assert "..." not in changelog
    assert f"{note_summary} (ab12cd34)" in changelog


def test_note_metadata_roundtrip_and_category_precedence():
    category, summary = parse_note_metadata(
        format_note("Added", "Added support for auto-tagging.")
    )

    assert category == "Added"
    assert summary == "Added support for auto-tagging."


def test_build_changelog_prefers_note_category_metadata():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "99999999",
            "fix(core): adjust parser",
            datetime(2026, 3, 7, tzinfo=UTC),
        )
    ]
    notes = {
        "99999999": "Category: Removed\n\nRemoved deprecated parser mode.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    assert "### Removed" in changelog
    assert "Removed deprecated parser mode. (99999999)" in changelog


def test_build_changelog_diversifies_repeated_leading_power_verbs():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "aaaa0001",
            "docs: first note",
            datetime(2026, 3, 8, tzinfo=UTC),
        ),
        make_commit(
            "bbbb0002",
            "docs: second note",
            datetime(2026, 3, 9, tzinfo=UTC),
        ),
    ]
    notes = {
        "aaaa0001": "Category: Fixed\n\nResolved timeout handling in the parser.",
        "bbbb0002": (
            "Category: Fixed\n\nResolved fallback behavior when retries are exhausted."
        ),
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    assert "Resolved timeout handling in the parser. (aaaa0001)" in changelog
    assert (
        "Corrected fallback behavior when retries are exhausted. (bbbb0002)"
        in changelog
    )


# ---------------------------------------------------------------------------
# Tests for merge_changelogs_with_keepachangelog and KAC helper functions
# ---------------------------------------------------------------------------


def test_extract_release_sections_kac_parses_headings_and_blocks():
    text = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Some change\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    sections = _extract_release_sections_kac(text)

    assert len(sections) == 2
    headings = [h for h, _ in sections]
    assert "## [Unreleased]" in headings
    assert "## [1.0.0] - 2026-01-01" in headings
    unreleased_block = next(b for h, b in sections if h == "## [Unreleased]")
    assert "Some change" in unreleased_block


def test_extract_release_sections_kac_returns_empty_for_no_headings():
    assert _extract_release_sections_kac("No headings here.\n") == []


def test_release_version_from_heading_kac_parses_semver():
    assert _release_version_from_heading_kac("## [1.2.3] - 2026-01-01") == "1.2.3"
    assert _release_version_from_heading_kac("## [v2.0.0]") == "2.0.0"


def test_release_version_from_heading_kac_returns_none_for_unreleased():
    assert _release_version_from_heading_kac("## [Unreleased]") is None


def test_release_version_from_heading_kac_returns_none_for_non_semver():
    assert _release_version_from_heading_kac("## [not-a-version]") is None


def test_is_unreleased_heading_matches_unreleased():
    assert _is_unreleased_heading("## [Unreleased]") is True
    assert _is_unreleased_heading("## [unreleased]") is True


def test_is_unreleased_heading_rejects_semver():
    assert _is_unreleased_heading("## [1.0.0] - 2026-01-01") is False
    assert _is_unreleased_heading("## [2.3.0]") is False


def test_find_insertion_point_kac_after_unreleased_section():
    text = (
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Old change\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    point = _find_insertion_point_kac(text)

    # Insertion point should be before "## [1.0.0]"
    assert text[point:].startswith("## [1.0.0]")


def test_find_insertion_point_kac_falls_back_to_first_release_when_no_unreleased():
    text = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n- Initial release\n"

    point = _find_insertion_point_kac(text)

    assert text[point:].startswith("## [1.0.0]")


def test_find_insertion_point_kac_returns_end_when_no_releases():
    text = "# Changelog\n\nNo releases yet.\n"

    point = _find_insertion_point_kac(text)

    assert point == len(text)


def test_merge_changelogs_with_keepachangelog_appends_new_version():
    existing = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    assert added == 1
    assert "## [1.1.0] - 2026-02-01" in merged
    assert "- Initial release" in merged
    # New section inserted after Unreleased, before existing 1.0.0
    assert merged.index("## [1.1.0]") < merged.index("## [1.0.0]")


def test_merge_changelogs_with_keepachangelog_skips_existing_version():
    existing = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release regenerated\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    assert added == 0
    assert merged == existing


def test_merge_changelogs_with_keepachangelog_skips_versions_older_than_max():
    existing = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [2.0.0] - 2026-03-01\n\n"
        "### Added\n"
        "- Major release\n"
    )
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [2.0.0] - 2026-03-01\n\n"
        "### Added\n"
        "- Major release\n\n"
        "## [1.9.0] - 2026-02-01\n\n"
        "### Added\n"
        "- Old version\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    assert added == 0
    assert "## [1.9.0]" not in merged


def test_merge_changelogs_with_keepachangelog_returns_generated_when_existing_empty():
    generated = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n- First release\n"

    merged, added = merge_changelogs_with_keepachangelog("", generated)

    assert added == 0
    assert merged == generated


def test_merge_changelogs_with_keepachangelog_handles_no_existing_releases():
    existing = "# Changelog\n\n## [Unreleased]\n\n### Changed\n- Placeholder\n"
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- First release\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    assert added == 1
    assert "## [1.0.0] - 2026-01-01" in merged
    assert "Placeholder" in merged


def test_build_renders_blank_line_between_md024_comment_and_heading():
    """The rendered changelog must have a blank line after the MD024 disable comment."""
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "aa000001",
            "feat: initial",
            datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    notes = {"aa000001": "Added first feature."}

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    # The blank line between the comment and the Changelog heading must be present
    assert "<!-- Markdownlint-disable MD024 -->\n\n# Changelog" in changelog


def test_infer_release_type_returns_patch_for_perf_and_revert():
    """'perf' and 'revert' commit types must produce a 'patch' release type."""
    assert infer_release_type("perf", False) == "patch"
    assert infer_release_type("revert", False) == "patch"


def test_parse_conventional_commit_empty_message_uses_unclassified_fallback():
    """An empty commit message must return 'Unclassified change' as description."""
    result = parse_conventional_commit("")

    assert result.description == "Unclassified change"
    assert result.commit_type is None


def test_parse_conventional_commit_non_conventional_has_none_commit_type():
    """Non-conventional commit messages must have commit_type set to None."""
    result = parse_conventional_commit("Updated README for clarity")

    assert result.commit_type is None
    assert result.description == "Updated README for clarity"


def test_is_unreleased_heading_case_insensitive():
    """Heading check must be case-insensitive to catch [Unreleased] in any case.

    This test catches equivalent mutations in the regex pattern (e.g., changing
    [Unreleased] to [unreleased]) because re.IGNORECASE makes them equivalent.
    """
    assert _is_unreleased_heading("## [Unreleased]") is True
    assert _is_unreleased_heading("## [unreleased]") is True
    assert _is_unreleased_heading("## [UNRELEASED]") is True
    assert _is_unreleased_heading("## [unRELEASED]") is True
    assert _is_unreleased_heading("## [v1.0.0]") is False
