from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Tuple

from click.testing import CliRunner

from ai_changelog_msg import main


class DummyRepo:

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path)
        self.cleared_namespace: Optional[str] = None

    def clear_notes(self, namespace: str) -> bool:
        self.cleared_namespace = namespace
        return True


class DummyProcessingRepo:

    def __init__(
        self, repo_path: str, commits, notes_by_commit=None, diff_by_commit=None
    ):
        self.repo_path = Path(repo_path)
        self._commits = commits
        self.notes_by_commit = notes_by_commit or {}
        self.diff_by_commit = diff_by_commit or {}
        self.saved_notes: List[Tuple[str, str, str]] = []
        self.created_tags: List[Tuple[str, str]] = []

    def get_all_commits(self, limit=None):
        return self._commits[:limit] if limit else self._commits

    def get_note(self, commit_hash: str, namespace: str):
        return self.notes_by_commit.get(commit_hash)

    def get_commit_diff(self, commit):
        return self.diff_by_commit.get(commit.hexsha, "")

    def set_note(self, commit_hash: str, content: str, namespace: str):
        self.notes_by_commit[commit_hash] = content
        self.saved_notes.append((commit_hash, content, namespace))

    def get_semantic_version_tags(self):
        return {}

    def create_tag(self, tag_name: str, commit_hash: str) -> bool:
        self.created_tags.append((tag_name, commit_hash))
        return True

    def get_commit_web_url(self, commit_hash: str):
        return f"https://example.test/commit/{commit_hash}"

    def resolve_output_path(self, file_path: str):
        return self.repo_path / file_path


class DummyTagRepo:

    def __init__(self, tags_by_commit, notes_by_commit=None):
        self.tags_by_commit = tags_by_commit
        self.notes_by_commit = notes_by_commit or {}
        self.created_tags = []

    def get_semantic_version_tags(self):
        return self.tags_by_commit

    def get_note(self, commit_hash: str, namespace: str):
        return self.notes_by_commit.get(commit_hash)

    def create_tag(self, tag_name: str, commit_hash: str) -> bool:
        self.created_tags.append((tag_name, commit_hash))
        return True


def test_cli_clear_all_removes_namespace_notes_and_exits(tmp_path, monkeypatch):
    repo = DummyRepo(str(tmp_path))

    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)

    def fail_ai_provider(config):
        raise AssertionError("AIProvider should not be constructed for --clear-all")

    monkeypatch.setattr(main, "AIProvider", fail_ai_provider)

    runner = CliRunner()
    result = runner.invoke(
        main.cli, [str(tmp_path), "--clear-all", "--namespace", "custom-notes"]
    )

    assert result.exit_code == 0
    assert repo.cleared_namespace == "custom-notes"
    assert "Removed all git notes from namespace: custom-notes" in result.output


def test_create_semver_tags_if_needed_creates_tags_when_none_exist():
    repo = DummyTagRepo(
        tags_by_commit={},
        notes_by_commit={
            "a1": "Category: Added\n\nAdded API endpoint.",
            "b2": "Category: Changed\n\nUpdated docs formatting.",
            "c3": "Category: Fixed\n\nFixed edge case handling.",
        },
    )
    commits = [
        SimpleNamespace(
            hexsha="a1",
            message="feat(api): add endpoint",
            committed_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            hexsha="b2",
            message="docs: update readme",
            committed_datetime=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            hexsha="c3",
            message="fix(api): handle edge case",
            committed_datetime=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
    ]

    created = main._create_semver_tags_if_needed(
        repo, commits, "ai-changelog", True, None
    )

    assert created == 3
    assert repo.created_tags == [
        ("v1.0.0", "a1"),
        ("v1.0.1", "b2"),
        ("v1.0.2", "c3"),
    ]


def test_create_semver_tags_if_needed_skips_when_semver_tags_exist():
    repo = DummyTagRepo(tags_by_commit={"abc": ["v2.3.4"]})
    commits = [
        SimpleNamespace(
            hexsha="a1",
            message="feat(api): add endpoint",
            committed_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ]

    created = main._create_semver_tags_if_needed(
        repo, commits, "ai-changelog", True, None
    )

    assert created == 0
    assert repo.created_tags == []


def test_create_semver_tags_if_needed_rejects_limit():
    repo = DummyTagRepo(tags_by_commit={})
    commits = []

    try:
        main._create_semver_tags_if_needed(repo, commits, "ai-changelog", True, 5)
    except ValueError as error:
        assert str(error) == "--create-semver-tags cannot be used with --limit"
    else:
        raise AssertionError(
            "Expected ValueError when using --create-semver-tags with --limit"
        )


def test_merge_missing_release_sections_appends_only_new_sections():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Existing entry\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Existing entry\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert existing in merged
    assert "## [1.1.0] - 2026-02-01" in merged


def test_merge_missing_release_sections_noop_when_all_exist():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 0
    assert merged == existing


def test_cli_processes_commits_upgrades_legacy_notes_and_writes_changelog(
    tmp_path, monkeypatch
):
    commits = [
        SimpleNamespace(
            hexsha="a1b2c3d4",
            message="feat(cli): add changelog output",
            committed_datetime=datetime(2026, 3, 1, tzinfo=timezone.utc),
            author=SimpleNamespace(name="Alice"),
        ),
        SimpleNamespace(
            hexsha="b2c3d4e5",
            message="fix(cli): handle legacy note",
            committed_datetime=datetime(2026, 3, 2, tzinfo=timezone.utc),
            author=SimpleNamespace(name="Bob"),
        ),
    ]
    repo = DummyProcessingRepo(
        str(tmp_path),
        commits=commits,
        notes_by_commit={"b2c3d4e5": "Legacy summary without category."},
        diff_by_commit={
            "a1b2c3d4": "+new line",
            "b2c3d4e5": "-old line\n+new line",
        },
    )

    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)

    class FakeAIProvider:

        def __init__(self, config):
            self.config = config

        def summarize_diff(self, commit_message, diff, author=None):
            return f"Added summary for {commit_message.split(':', 1)[0]}."

        def generate_changelog_entry(self, commit_message, note, category, is_breaking):
            return note.splitlines()[0] if note else commit_message

    monkeypatch.setattr(main, "AIProvider", FakeAIProvider)

    runner = CliRunner()
    result = runner.invoke(
        main.cli,
        [str(tmp_path), "--create-semver-tags", "--changelog-file", "CHANGELOG.md"],
    )

    assert result.exit_code == 0
    assert any("Category: Added" in note for _, note, _ in repo.saved_notes)
    assert any("Category: Fixed" in note for _, note, _ in repo.saved_notes)
    assert repo.created_tags == [("v1.0.0", "a1b2c3d4"), ("v1.0.1", "b2c3d4e5")]
    changelog_text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.0.1] - 2026-03-02" in changelog_text
    assert "## [1.0.0] - 2026-03-01" in changelog_text


def test_cli_reports_no_commits_and_exits(tmp_path, monkeypatch):
    repo = DummyProcessingRepo(str(tmp_path), commits=[])
    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)

    class FakeAIProvider:

        def __init__(self, config):
            self.config = config

    monkeypatch.setattr(main, "AIProvider", FakeAIProvider)

    runner = CliRunner()
    result = runner.invoke(main.cli, [str(tmp_path)])

    assert result.exit_code == 0
    assert "No commits found in repository" in result.output
