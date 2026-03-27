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

from datetime import datetime, timezone
from types import SimpleNamespace

from ai_changelog_msg.changelog import (
    ChangelogBuilder,
    format_note,
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
            datetime(2026, 3, 10, tzinfo=timezone.utc),
        ),
        make_commit(
            "22222222",
            "feat(cli): generate changelog",
            datetime(2026, 3, 11, tzinfo=timezone.utc),
        ),
        make_commit(
            "33333333",
            "fix(notes): handle empty note",
            datetime(2026, 3, 12, tzinfo=timezone.utc),
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
            datetime(2026, 3, 1, tzinfo=timezone.utc),
        ),
        make_commit(
            "bbbbbbb2",
            "fix: patch release bug",
            datetime(2026, 3, 2, tzinfo=timezone.utc),
        ),
        make_commit(
            "ccccccc3",
            "feat(api): add comparison mode",
            datetime(2026, 3, 3, tzinfo=timezone.utc),
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
            datetime(2026, 3, 4, tzinfo=timezone.utc),
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
            datetime(2026, 3, 5, tzinfo=timezone.utc),
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
            datetime(2026, 3, 6, tzinfo=timezone.utc),
        )
    ]
    notes = {
        "fffffff6": "Removed obsolete compatibility paths from the project.",
    }
    removal_heavy_diff = "\n".join(
        [
            "diff --git a/x b/x",
            "--- a/x",
            "+++ b/x",
            "@@ -1,4 +0,0 @@",
            "-line one",
            "-line two",
            "-line three",
        ]
    )

    changelog = builder.build(
        commits=commits,
        get_note=lambda commit_hash, namespace: notes.get(commit_hash),
        tags_by_commit={},
        get_diff=lambda commit: removal_heavy_diff,
    )

    assert "### Removed" in changelog


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
            datetime(2026, 3, 7, tzinfo=timezone.utc),
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
