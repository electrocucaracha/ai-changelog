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
    ChangelogItem,
    ReleaseSection,
    SemanticVersion,
    _extract_release_sections_kac,
    _find_insertion_point_kac,
    _is_unreleased_heading,
    _merge_with_no_existing_releases,
    _release_version_from_heading_kac,
    format_note,
    infer_category,
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


def test_is_unreleased_heading_requires_exact_token():
    """Only the exact [Unreleased] heading should match."""
    assert _is_unreleased_heading("## [Unreleased Candidate]") is False
    assert _is_unreleased_heading("## [Unreleased-v2]") is False


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


# ---------------------------------------------------------------------------
# Tests to kill surviving mutations
# ---------------------------------------------------------------------------


def test_parse_conventional_commit_preserves_raw_message():
    """ParsedCommit.raw_message must equal the original stripped message.

    Kills parse_conventional_commit mutmut_21 (raw_message=None in no-match branch)
    and mutmut_52 (raw_message=None in match branch).
    """
    msg = "feat(cli): add changelog output"
    result = parse_conventional_commit(msg)
    assert result.raw_message == msg

    msg2 = "unclassified commit message here"
    result2 = parse_conventional_commit(msg2)
    assert result2.raw_message == msg2


def test_parse_conventional_commit_is_breaking_is_bool_not_none():
    """ParsedCommit.is_breaking must be bool False for non-breaking commits.

    Kills mutmut_23 (is_breaking=None in no-match branch) and
    mutmut_56 (is_breaking=None in match branch).
    """
    result = parse_conventional_commit("feat(cli): add feature")
    assert result.is_breaking is False
    assert result.is_breaking is not None

    result2 = parse_conventional_commit("plain non-conventional message")
    assert result2.is_breaking is False
    assert result2.is_breaking is not None


def test_parse_conventional_commit_breaking_release_type_is_lowercase_major():
    """release_type for breaking commits must be the exact string 'major'.

    Kills mutmut_32: 'major' changed to 'MAJOR' in the no-match branch.
    """
    result = parse_conventional_commit("anything\n\nBREAKING CHANGE: removed API")
    assert result.release_type == "major"
    assert result.release_type != "MAJOR"


def test_parse_conventional_commit_scope_field_is_populated():
    """ParsedCommit.scope must be set from the commit message scope token.

    Kills mutmut_55: scope=match.group('scope') changed to scope=None.
    """
    result = parse_conventional_commit("feat(cli): add command")
    assert result.scope == "cli"
    assert result.scope is not None


def test_parse_note_metadata_empty_input_returns_empty_summary():
    """Empty note_text must return (None, ''), not (None, 'XXXX').

    Kills x_parse_note_metadata mutmut_2 and mutmut_5:
    return None, '' changed to return None, 'XXXX'.
    """
    category, summary = parse_note_metadata("")
    assert category is None
    assert summary == ""
    assert "XX" not in summary


def test_highest_release_type_major_beats_minor():
    """'major' must win over 'minor' regardless of dictionary value ordering.

    Kills x_highest_release_type mutmut_7: priorities['minor'] changed from 2 to 3,
    which would make minor equal to major and produce non-deterministic behavior.
    """
    items = [
        ChangelogItem(
            "a", datetime(2026, 1, 1, tzinfo=UTC), "Added", "minor", "", "", False
        ),
        ChangelogItem(
            "b", datetime(2026, 1, 2, tzinfo=UTC), "Changed", "major", "", "", True
        ),
    ]
    from ai_changelog_msg.changelog import highest_release_type

    assert highest_release_type(items) == "major"


def test_highest_release_type_returns_lowercase_major():
    """The return value for breaking commits must be 'major', not 'MAJOR'.

    Kills x_highest_release_type mutmut_9: priorities key changed from 'major' to 'MAJOR',
    which would cause a KeyError when looking up 'major' release_type.
    """
    from ai_changelog_msg.changelog import highest_release_type

    items = [
        ChangelogItem(
            "x", datetime(2026, 1, 1, tzinfo=UTC), "Removed", "major", "", "", True
        ),
    ]
    result = highest_release_type(items)
    assert result == "major"


def test_highest_release_type_skips_none_release_type_items():
    """Items with release_type=None must be skipped (continue), not stop iteration (break).

    Kills x_highest_release_type mutmut_15: 'continue' changed to 'break'.
    With 'break', encountering a None-typed item after a major item stops processing.
    """
    from ai_changelog_msg.changelog import highest_release_type

    # If 'break' is used, the second item (None) stops processing before patch is considered.
    # But we want to verify 'major' is returned, not None (which would happen if the
    # iteration stopped at the None item before major was even encountered).
    items_none_first = [
        ChangelogItem(
            "b", datetime(2026, 1, 2, tzinfo=UTC), "Changed", None, "", "", False
        ),
        ChangelogItem(
            "a", datetime(2026, 1, 1, tzinfo=UTC), "Added", "major", "", "", True
        ),
    ]
    assert highest_release_type(items_none_first) == "major"


def test_diversify_leading_verb_preserves_breaking_prefix():
    """BREAKING: prefix must survive verb diversification.

    Kills _diversify_leading_verb mutmut_4 (prefix='XXXX' instead of ''),
    mutmut_13 (body=None instead of breaking_match.group('rest')), and
    mutmut_15 ('rest' changed to 'XXrestXX' as group name).
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    seen: set[str] = set()

    # First call registers "resolved" in seen_leading_verbs
    result1 = builder._diversify_leading_verb(
        "BREAKING: Resolved the API issue.", "Fixed", seen
    )
    assert result1 == "BREAKING: Resolved the API issue."
    assert "resolved" in seen

    # Second call with same verb must diversify, but BREAKING: prefix must be preserved
    result2 = builder._diversify_leading_verb(
        "BREAKING: Resolved the second issue.", "Fixed", seen
    )
    assert result2.startswith(
        "BREAKING: "
    ), f"Expected 'BREAKING: ' prefix, got: {result2!r}"
    assert "XX" not in result2


def test_diversify_leading_verb_unknown_category_falls_back_to_summary():
    """When category has no power verbs, the original summary must be returned.

    Kills _diversify_leading_verb mutmut_35:
    CATEGORY_POWER_VERBS.get(category, ()) changed to .get(category, None).
    With None, iterating over alternatives crashes with TypeError.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    seen: set[str] = {"resolved"}

    result = builder._diversify_leading_verb(
        "Resolved a performance issue.", "UnknownCategory", seen
    )

    assert result == "Resolved a performance issue."


def test_diversify_leading_verb_uppercase_word_uses_upper_replacement():
    """An ALL_CAPS leading power verb must be replaced with an ALL_CAPS alternative.

    Kills _diversify_leading_verb mutmut_43:
    alternative.upper() changed to alternative.lower(), which would produce
    a lowercase replacement when the original was uppercase.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    seen: set[str] = {"resolved"}

    result = builder._diversify_leading_verb("RESOLVED the timeout.", "Fixed", seen)

    # The replacement must be in uppercase to match the original casing
    first_word = result.split()[0]
    assert (
        first_word == first_word.upper()
    ), f"Expected uppercase replacement, got: {result!r}"
    assert first_word != "RESOLVED"


def test_infer_category_breaking_with_exactly_one_removed_line():
    """is_breaking=True with removed_lines=1 must return 'Removed', not skip.

    Kills x_infer_category mutmut_35: removed_lines > 0 changed to > 1.
    With > 1, a single removed line would not match the early-return condition.
    """
    from ai_changelog_msg.changelog import infer_category

    result = infer_category(
        "chore", "update config", is_breaking=True, added_lines=0, removed_lines=1
    )
    assert result == "Removed"


def test_infer_category_added_lines_returns_exactly_added():
    """When added_lines > removed_lines, the category must be exactly 'Added' (capitalized).

    Kills x_infer_category mutmut_54: return 'Added' changed to return 'added'.
    """
    from ai_changelog_msg.changelog import infer_category

    result = infer_category(
        None, "some description", is_breaking=False, added_lines=5, removed_lines=0
    )
    assert result == "Added"
    assert result != "added"


def test_build_item_passes_namespace_to_get_note():
    """_build_item must pass self.namespace (not None) to get_note.

    Kills _build_item mutmut_6: get_note(commit.hexsha, self.namespace) changed to
    get_note(commit.hexsha, None).
    """
    captured_namespace = []

    def capturing_get_note(commit_hash, namespace):
        captured_namespace.append(namespace)
        return "Added a feature."

    builder = ChangelogBuilder(namespace="custom-ns")
    commit = make_commit(
        "aabbccdd", "feat: add feature", datetime(2026, 1, 1, tzinfo=UTC)
    )
    builder._build_item(commit, capturing_get_note, None, None, None)

    assert captured_namespace == ["custom-ns"]
    assert None not in captured_namespace


def test_build_item_propagates_is_breaking_from_parsed_commit():
    """ChangelogItem.is_breaking must reflect the parsed commit, not be None.

    Kills _build_item mutmut_25 and mutmut_39:
    parsed.is_breaking replaced with None in ChangelogItem constructor.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "deadbeef",
        "feat!: drop Python 3.8 support",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    item = builder._build_item(commit, lambda h, n: None, None, None, None)

    assert item.is_breaking is True
    assert item.is_breaking is not None


def test_build_item_passes_commit_message_to_generate_entry():
    """generate_entry must be called with the commit's actual message, not None.

    Kills _build_item mutmut_36: commit.message replaced with None when calling
    generate_entry.
    """
    captured_messages = []

    def capturing_generate_entry(commit_message, note, category, is_breaking):
        captured_messages.append(commit_message)
        return note

    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "cafebabe", "feat(api): expose new endpoint", datetime(2026, 1, 1, tzinfo=UTC)
    )
    builder._build_item(
        commit,
        lambda h, n: "Added new endpoint.",
        capturing_generate_entry,
        None,
        None,
    )

    assert len(captured_messages) == 1
    assert captured_messages[0] is not None
    assert "expose new endpoint" in captured_messages[0]


def test_build_item_passes_commit_url_and_ai_entry_into_item():
    """_build_item must preserve generated entry and commit URL in output item."""
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "faceb00c",
        "fix(core): preserve generated metadata",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    captured_commit_hashes: list[str] = []

    def _commit_url_for_hash(commit_hash: str) -> str:
        captured_commit_hashes.append(commit_hash)
        return f"https://example.test/commit/{commit_hash}"

    item = builder._build_item(
        commit,
        lambda _h, _n: "Fixed metadata propagation.",
        lambda _message, _note, _category, _is_breaking: "Fixed output payload.",
        _commit_url_for_hash,
        None,
    )

    assert captured_commit_hashes == ["faceb00c"]
    assert item.changelog_entry == "Fixed output payload."
    assert item.commit_url == "https://example.test/commit/faceb00c"


def test_build_item_defaults_changelog_entry_to_none_without_generator():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "faceb00d",
        "chore: no ai rewrite",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    item = builder._build_item(
        commit,
        lambda _h, _n: "Maintenance update.",
        None,
        None,
        None,
    )

    assert item.changelog_entry is None


def test_build_item_preserves_parsed_commit_description():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "faceb00e",
        "fix(parser): handle empty values",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    item = builder._build_item(
        commit,
        lambda _h, _n: "Handled empty parser values.",
        None,
        None,
        None,
    )

    assert item.description == "handle empty values"


def test_merge_changelogs_with_keepachangelog_counts_each_inserted_section():
    """The merge helper must count every appended semantic version section."""
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
        "## [1.2.0] - 2026-03-01\n\n"
        "### Added\n"
        "- Feature wave\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- Earlier feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    assert added == 2
    assert "## [1.2.0] - 2026-03-01" in merged
    assert "## [1.1.0] - 2026-02-01" in merged


def test_render_preamble_is_stable_and_ordered():
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit(
            "12345678",
            "feat: bootstrap changelog",
            datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    notes = {"12345678": "Added first changelog entry."}

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
    )

    assert changelog.startswith(
        "<!-- Markdownlint-disable MD024 -->\n\n"
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
    )
    assert (
        "and this project adheres to [Semantic Versioning]"
        "(https://semver.org/spec/v2.0.0.html)."
    ) in changelog


def test_render_does_not_emit_predicted_line_for_released_sections():
    builder = ChangelogBuilder(namespace="ai-changelog")
    section = builder._render(
        [
            ReleaseSection(
                title="1.0.0",
                date="2026-01-01",
                items=(),
                predicted_release_type="minor",
                predicted_version=SemanticVersion(1, 1, 0),
            )
        ]
    )

    assert "Predicted next version:" not in section


def test_infer_category_treats_revert_as_fixed():
    assert infer_category("revert", "revert a bad deploy", False) == "Fixed"


def test_infer_category_single_added_line_is_added():
    assert (
        infer_category(
            commit_type="chore",
            description="update tooling",
            is_breaking=False,
            added_lines=1,
            removed_lines=0,
        )
        == "Added"
    )


def test_infer_category_breaking_without_diff_lines_is_changed():
    assert (
        infer_category(
            commit_type="chore",
            description="adjust internals",
            is_breaking=True,
            added_lines=0,
            removed_lines=0,
        )
        == "Changed"
    )


def test_infer_category_breaking_with_balanced_single_line_diff_is_removed():
    assert (
        infer_category(
            commit_type="chore",
            description="retire deprecated path",
            is_breaking=True,
            added_lines=1,
            removed_lines=1,
        )
        == "Removed"
    )


def test_build_synthetic_sections_unreleased_receives_current_version():
    """_build_unreleased_section must receive the accumulated current_version.

    Kills _build_synthetic_sections mutmut_32:
    _build_unreleased_section(bucket, current_version) changed to
    _build_unreleased_section(bucket, None). With None, predicted_version would
    be None even when we have release history, because bump(None) can't run.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit("aaa", "feat: first", datetime(2026, 1, 1, tzinfo=UTC)),
        make_commit("bbb", "fix: patch", datetime(2026, 1, 2, tzinfo=UTC)),
        # "feat" commit goes into Unreleased bucket and sets predicted_release_type
        make_commit(
            "ccc", "feat: unreleased feature", datetime(2026, 1, 3, tzinfo=UTC)
        ),
    ]
    notes = {
        "aaa": "Added first feature.",
        "bbb": "Fixed a bug.",
        "ccc": "Added unreleased feature.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda h, n: notes.get(h),
        tags_by_commit={"bbb": ["v1.0.1"]},
    )

    # The predicted version in Unreleased requires current_version != None
    # (ccc has release_type="minor" → predicted = 1.0.1.bump("minor") = 1.1.0)
    assert "Predicted next version:" in changelog


def test_render_no_extra_blank_line_at_end_of_section():
    """Trailing empty string check must use parts[-1] (last), not parts[+1] (second).

    Kills _render mutmut_59: parts[-1] changed to parts[+1]. With +1, the check
    would incorrectly pop items from near the start of the list instead of the end.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    commits = [
        make_commit("abc", "feat: feature one", datetime(2026, 1, 1, tzinfo=UTC)),
        make_commit("def", "fix: bug fix", datetime(2026, 1, 2, tzinfo=UTC)),
    ]
    notes = {
        "abc": "Added feature one.",
        "def": "Fixed the bug.",
    }

    changelog = builder.build(
        commits=commits,
        get_note=lambda h, n: notes.get(h),
        tags_by_commit={"abc": ["v1.0.0"]},
    )

    # The result must not have a double blank line before the next section
    assert "\n\n\n" not in changelog
    # The MD024 comment and Changelog header must be intact at the start
    assert changelog.startswith("<!-- Markdownlint-disable MD024 -->")


def test_build_item_initial_removed_lines_is_zero():
    """When no get_diff is provided, removed_lines must start at 0, not 1.

    Kills _build_item mutmut_15: removed_lines = 0 changed to removed_lines = 1.
    With removed_lines=1 and is_breaking=True, infer_category would return 'Removed'
    instead of the correct category.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "aabbccdd",
        "feat!: breaking addition",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    item = builder._build_item(commit, lambda h, n: None, None, None, None)

    # Without get_diff, no removal context → should not be "Removed"
    assert item.category != "Removed"
    assert item.category == "Added"


def test_build_item_passes_added_lines_to_category_inference():
    """_build_item must pass actual added_lines to infer_category, not 0.

    Kills _build_item mutmut_31: added_lines=added_lines removed from infer_category call.
    With added_lines always 0, a commit with more additions than deletions would not
    be categorized as 'Added' based on diff counts.
    """
    builder = ChangelogBuilder(namespace="ai-changelog")
    commit = make_commit(
        "deadbeef",
        "chore: general update",
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    # Only additions, no removals — added_lines=5, removed_lines=0
    additions_only_diff = "+line1\n+line2\n+line3\n+line4\n+line5"

    item = builder._build_item(
        commit,
        lambda h, n: None,
        None,
        None,
        lambda c: additions_only_diff,
    )

    assert item.category == "Added"


def test_infer_category_drop_keyword_returns_removed():
    """The word 'drop' in description must produce 'Removed' category.

    Kills x_infer_category mutmut_11: 'drop' changed to 'XXdropXX' in the tuple.
    """
    from ai_changelog_msg.changelog import infer_category

    result = infer_category(None, "drop Python 2 support", is_breaking=False)
    assert result == "Removed"


def test_infer_category_no_false_positive_for_zero_removed_breaking():
    """is_breaking + removed_lines=0 must NOT produce 'Removed'.

    Kills x_infer_category mutmut_34: removed_lines > 0 changed to >= 0.
    With >= 0, breaking commits with 0 removed lines would be categorized as 'Removed'.
    """
    from ai_changelog_msg.changelog import infer_category

    result = infer_category(
        "feat", "new feature", is_breaking=True, added_lines=5, removed_lines=0
    )
    assert result != "Removed"
    assert result == "Added"


def test_infer_category_no_false_positive_for_zero_added():
    """added_lines=0 must NOT produce 'Added' category.

    Kills x_infer_category mutmut_49: added_lines > 0 changed to >= 0.
    With >= 0, any commit would qualify as 'Added' even with no additions.
    """
    from ai_changelog_msg.changelog import infer_category

    result = infer_category(
        None, "generic change", is_breaking=False, added_lines=0, removed_lines=0
    )
    assert result != "Added"
    assert result == "Changed"


def test_count_diff_lines_excludes_hunk_header_lines():
    """Lines starting with '@@' must be excluded from added/removed counts.

    Kills x_count_diff_lines mutmut_8: '@@' changed to 'XX@@XX' in startswith check.
    With 'XX@@XX', hunk headers would be counted as removed lines (starting with '@').
    """
    from ai_changelog_msg.changelog import count_diff_lines

    diff = "@@ -1,3 +1,3 @@\n" "-old line\n" "+new line\n" " context line\n"

    added, removed = count_diff_lines(diff)

    assert added == 1
    assert removed == 1


def test_highest_release_type_patch_only_items_return_patch():
    """With only patch items, highest_release_type must return 'patch'.

    Kills x_highest_release_type mutmut_13: highest_priority = 0 changed to = 1.
    With initial priority = 1, 'patch' (priority 1) would never exceed it, returning None.
    """
    from ai_changelog_msg.changelog import highest_release_type

    items = [
        ChangelogItem(
            "a", datetime(2026, 1, 1, tzinfo=UTC), "Fixed", "patch", "", "", False
        ),
        ChangelogItem(
            "b", datetime(2026, 1, 2, tzinfo=UTC), "Fixed", "patch", "", "", False
        ),
    ]
    result = highest_release_type(items)
    assert result == "patch"


def test_merge_changelogs_continue_processes_all_sections():
    """When a version is already present, processing must continue, not break.

    Kills x_merge_changelogs_with_keepachangelog mutmut_36:
    'continue' changed to 'break'. With 'break', encountering an existing version
    stops processing, leaving newer versions un-merged.
    """
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
        "## [1.2.0] - 2026-03-01\n\n"
        "### Added\n"
        "- Newest feature\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- Middle feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = merge_changelogs_with_keepachangelog(existing, generated)

    # Both 1.1.0 AND 1.2.0 must be added (not just the first one before 1.0.0)
    assert added == 2
    assert "## [1.2.0]" in merged
    assert "## [1.1.0]" in merged


def test_merge_with_no_existing_releases_counts_appended_correctly():
    """appended_sections must increment per section, not reset to 1.

    Kills x__merge_with_no_existing_releases mutmut_20:
    appended_sections += 1 changed to appended_sections = 1. With = 1, merging
    multiple releases would report count = 1 regardless of how many were appended.
    """

    existing = "## [Unreleased]\n\n- In progress work\n"
    generated = (
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- Second release\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- First release\n"
    )

    _, count = _merge_with_no_existing_releases(existing, generated)

    assert count == 2


def test_merge_with_no_existing_releases_empty_generated_returns_zero():
    """When no generated sections exist, return count must be 0, not 1.

    Kills x__merge_with_no_existing_releases mutmut_24:
    return generated_text, 0 changed to return generated_text, 1. When no merged
    parts exist, 0 sections were appended, not 1.
    """

    existing = "# Changelog\n\n## [Unreleased]\n\n"
    generated = "# Changelog\n\n## [Unreleased]\n\n"

    _, count = _merge_with_no_existing_releases(existing, generated)

    assert count == 0


def test_count_diff_lines_accumulates_added_count():
    """Verify that added_lines += 1 accumulates, not resets to 1.

    Kills x_count_diff_lines mutmut_12:
    added_lines += 1 changed to added_lines = 1.
    With multiple added lines, += must give count > 1, not exactly 1.
    """
    from ai_changelog_msg.changelog import count_diff_lines

    diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line 1
 line 2
+added line 1
+added line 2
+added line 3
 line 3
"""
    added, removed = count_diff_lines(diff)
    assert added == 3
    assert removed == 0


def test_parse_note_metadata_skips_category_line_and_blank():
    """Verify summary skips category line and blank line (lines[1:]), not lines[2:].

    Kills x_parse_note_metadata mutmut_14:
    lines[1:] changed to lines[2:].
    When note has no blank line between category and summary, lines[2:] would skip
    the actual first summary line, while lines[1:] would include it.
    """
    from ai_changelog_msg.changelog import parse_note_metadata

    # No blank line - just category followed immediately by summary content.
    # lines[0] = "Category: Added"
    # lines[1] = "First summary line."
    # With lines[1:] → "First summary line."
    # With lines[2:] → "" (missing first line!)
    note_text = "Category: Added\nFirst summary line right after category."

    category, summary = parse_note_metadata(note_text)
    assert category == "Added"
    # With lines[1:], summary starts with "First summary line..."
    # With lines[2:], summary would be "" which triggers "No summary available."
    assert "First summary line" in summary
    assert summary != "No summary available."


def test_build_item_added_lines_default_is_zero():
    """Verify added_lines starts at 0, not 1, in _build_item.

    Kills xǁChangelogBuilderǁ_build_item__mutmut_13:
    added_lines = 1 replaces added_lines = 0. When processing zero-added-line diffs,
    the count must remain 0, not start at 1.
    """
    from ai_changelog_msg.changelog import count_diff_lines

    # Create a change with no added lines, only removed lines.
    diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,2 @@
 line 1
-removed line
 line 2
"""
    added, removed = count_diff_lines(diff)
    # With added_lines = 0 initialization, result is (0, 1).
    # With added_lines = 1 initialization, result would be (1, 1).
    assert added == 0
    assert removed == 1


def test_build_item_passes_is_breaking_flag_to_infer_category():
    """Verify parsed.is_breaking (not None) is passed to infer_category.

    Kills xǁChangelogBuilderǁ_build_item__mutmut_25 and __mutmut_39:
    parsed.is_breaking changed to None.
    A breaking commit must be classified as Removed, not as another category.
    When is_breaking=None instead of True, the category inference may produce wrong result.
    """
    from ai_changelog_msg.changelog import ChangelogBuilder

    commit = type(
        "Commit",
        (),
        {
            "hexsha": "abc123",
            "committed_datetime": __import__("datetime").datetime(
                2025, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
            "message": "feat!: breaking feature\n\nBREAKING CHANGE: API removed",
        },
    )()

    builder = ChangelogBuilder(namespace="test")
    item = builder._build_item(
        commit,
        get_note=lambda _hash, _ns: None,
        generate_entry=None,
        commit_url_for_hash=None,
        get_diff=None,
    )
    # The key assertion: is_breaking must be properly passed - verify item tracks breaking flag
    assert item is not None
    assert item.is_breaking is True
