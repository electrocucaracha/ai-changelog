from __future__ import annotations

# pylint: disable=too-many-lines
import logging
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from click.testing import CliRunner

from ai_changelog_msg import main


class DummyRepo:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path)
        self.cleared_namespace: str | None = None

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
        self.saved_notes: list[tuple[str, str, str]] = []
        self.created_tags: list[tuple[str, str]] = []

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


def _invoke_cli_with_dummy_repo(tmp_path, monkeypatch, args: list[str]):
    repo = DummyRepo(str(tmp_path))
    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)

    runner = CliRunner()
    result = runner.invoke(main.cli, [str(tmp_path), *args])
    return repo, result


def _build_commit(
    hexsha: str,
    message: str,
    committed_datetime: datetime,
    author_name: str,
) -> SimpleNamespace:
    """Build a lightweight commit object for CLI tests."""
    return SimpleNamespace(
        hexsha=hexsha,
        message=message,
        committed_datetime=committed_datetime,
        author=SimpleNamespace(name=author_name),
    )


def _build_processing_repo(
    tmp_path,
    commits,
    notes_by_commit=None,
    diff_by_commit=None,
):
    """Create a dummy processing repository with optional notes and diffs."""
    return DummyProcessingRepo(
        str(tmp_path),
        commits=commits,
        notes_by_commit=notes_by_commit,
        diff_by_commit=diff_by_commit,
    )


def _patch_processing_repo(monkeypatch, repo) -> None:
    """Patch GitRepository constructor to return the provided dummy repo."""
    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)


def _install_fake_ai_provider(
    monkeypatch,
    *,
    summary_text: str = "Added summary.",
    fail_on_summarize: bool = False,
    fail_on_generate_entry: bool = False,
) -> None:
    """Install a predictable AI provider test double for CLI tests."""

    class FakeAIProvider:
        def __init__(self, config):
            self.config = config

        def summarize_diff(self, commit_message, diff, author=None):
            if fail_on_summarize:
                raise AssertionError("summarize_diff should not be called")
            return summary_text

        def generate_changelog_entry(self, commit_message, note, category, is_breaking):
            if fail_on_generate_entry:
                raise AssertionError("generate_changelog_entry should not be called")
            return note.splitlines()[0] if note else commit_message

    monkeypatch.setattr(main, "AIProvider", FakeAIProvider)


def _invoke_cli(tmp_path, args: list[str]):
    """Invoke the CLI with a repository path and additional arguments."""
    runner = CliRunner()
    return runner.invoke(main.cli, [str(tmp_path), *args])


def _setup_single_commit_repo(
    tmp_path,
    monkeypatch,
    *,
    notes_by_commit=None,
    diff_by_commit=None,
):
    """Set up a one-commit processing repo and patch GitRepository to return it."""
    commits = [
        _build_commit(
            "a1b2c3d4",
            "feat(cli): add changelog output",
            datetime(2026, 3, 1, tzinfo=UTC),
            "Alice",
        )
    ]
    repo = _build_processing_repo(
        tmp_path,
        commits=commits,
        notes_by_commit=notes_by_commit,
        diff_by_commit=diff_by_commit or {"a1b2c3d4": "+new line"},
    )
    _patch_processing_repo(monkeypatch, repo)
    return repo


def _build_prepared_commit(hexsha: str, author_name: str, message: str, diff: str):
    """Create a prepared commit record for summary generation tests."""
    return main._PreparedCommit(
        commit=SimpleNamespace(hexsha=hexsha, author=SimpleNamespace(name=author_name)),
        commit_message=message,
        category="Added",
        existing_note=None,
        diff=diff,
    )


def _run_summary_generation_with_output_capture(
    monkeypatch,
    *,
    is_tty: bool,
    prepared,
    workers: int,
):
    """Run concurrent summary generation while capturing click output chunks."""
    output_chunks: list[str] = []

    monkeypatch.setattr(main.sys.stdout, "isatty", lambda: is_tty)
    monkeypatch.setattr(
        main.click, "echo", lambda text="", nl=True: output_chunks.append(text)
    )

    class FastProvider:
        def summarize_diff(self, commit_message, diff, author=None):
            return "ok"

    results = main._generate_summaries_concurrently(
        cast(main.AIProvider, FastProvider()),
        prepared,
        workers,
    )
    return results, output_chunks


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


def test_cli_reads_options_from_environment_variables(tmp_path, monkeypatch):
    repo = DummyRepo(str(tmp_path))
    monkeypatch.setattr(main, "GitRepository", lambda repo_path: repo)

    monkeypatch.setenv("CHANGELOG_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("CHANGELOG_NAMESPACE", "env-notes")
    monkeypatch.setenv("CHANGELOG_FORCE", "1")
    monkeypatch.setenv("CHANGELOG_CLEAR_ALL", "1")
    monkeypatch.setenv("CHANGELOG_CREATE_SEMVER_TAGS", "1")
    monkeypatch.setenv("CHANGELOG_LIMIT", "5")
    monkeypatch.setenv("CHANGELOG_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CHANGELOG_CHANGELOG_FILE", "docs/CHANGELOG.md")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("CHANGELOG_LITELLM_HEADERS_JSON", '{"X-Team":"devtools"}')

    runner = CliRunner()
    result = runner.invoke(main.cli, [str(tmp_path)])

    assert result.exit_code == 0
    assert repo.cleared_namespace == "env-notes"
    assert "--model gpt-4o-mini" in result.output
    assert "--namespace env-notes" in result.output
    assert "--force" in result.output
    assert "--clear-all" in result.output
    assert "--create-semver-tags" in result.output
    assert "--limit 5" in result.output
    assert "--log-level DEBUG" in result.output
    assert "--changelog-file docs/CHANGELOG.md" in result.output
    assert "--litellm-api-base" not in result.output
    assert "--litellm-api-key" not in result.output
    assert "--litellm-headers-json '$CHANGELOG_LITELLM_HEADERS_JSON'" in result.output


def test_cli_includes_workers_in_execution_command(tmp_path, monkeypatch):
    _, result = _invoke_cli_with_dummy_repo(
        tmp_path, monkeypatch, ["--clear-all", "--workers", "7"]
    )

    assert result.exit_code == 0
    assert "--workers 7" in result.output


def test_cli_includes_retry_flags_in_execution_command(tmp_path, monkeypatch):
    _, result = _invoke_cli_with_dummy_repo(
        tmp_path,
        monkeypatch,
        [
            "--clear-all",
            "--retry-attempts",
            "5",
            "--retry-backoff-seconds",
            "2.5",
        ],
    )

    assert result.exit_code == 0
    assert "--retry-attempts 5" in result.output
    assert "--retry-backoff-seconds 2.5" in result.output


def test_cli_includes_overall_progress_mode_in_execution_command(tmp_path, monkeypatch):
    _, result = _invoke_cli_with_dummy_repo(
        tmp_path,
        monkeypatch,
        ["--clear-all", "--overall-progress-mode", "work-units"],
    )

    assert result.exit_code == 0
    assert "--overall-progress-mode work-units" in result.output


def test_resolve_worker_count_auto_and_override(monkeypatch):
    monkeypatch.setattr(main.os, "cpu_count", lambda: 12)

    assert main._resolve_worker_count(None, 2) == 2
    assert main._resolve_worker_count(None, 20) == 12
    assert main._resolve_worker_count(5, 20) == 5
    assert main._resolve_worker_count(50, 3) == 3


def test_resolve_overall_progress_total_modes():
    assert main._resolve_overall_progress_total("commits", 57, 57) == 57
    assert main._resolve_overall_progress_total("work-units", 57, 57) == 114


def test_cli_prints_auto_selected_worker_count(tmp_path, monkeypatch):
    _setup_single_commit_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(main.os, "cpu_count", lambda: 8)
    _install_fake_ai_provider(monkeypatch)

    result = _invoke_cli(tmp_path, [])

    assert result.exit_code == 0
    assert "Using 1 worker(s) (auto-selected from 8 CPU core(s))" in result.output


def test_cli_prints_explicit_worker_count(tmp_path, monkeypatch):
    _setup_single_commit_repo(tmp_path, monkeypatch)
    _install_fake_ai_provider(monkeypatch)

    result = _invoke_cli(tmp_path, ["--workers", "4"])

    assert result.exit_code == 0
    assert "Using 1 worker(s) (from --workers)" in result.output


def test_cli_prints_per_worker_summary_progress(tmp_path, monkeypatch):
    commits = [
        _build_commit(
            "a1b2c3d4",
            "feat(cli): add changelog output",
            datetime(2026, 3, 1, tzinfo=UTC),
            "Alice",
        ),
        _build_commit(
            "b2c3d4e5",
            "fix(cli): refine parsing",
            datetime(2026, 3, 2, tzinfo=UTC),
            "Bob",
        ),
    ]
    repo = _build_processing_repo(
        tmp_path,
        commits=commits,
        diff_by_commit={
            "a1b2c3d4": "+new line",
            "b2c3d4e5": "+another line",
        },
    )

    _patch_processing_repo(monkeypatch, repo)
    _install_fake_ai_provider(monkeypatch)

    result = _invoke_cli(tmp_path, ["--workers", "2"])

    assert result.exit_code == 0
    assert "Overall progress mode: commits" in result.output
    assert "Overall progress" in result.output
    assert "Per-worker summary progress:" in result.output
    assert "Worker  1:" in result.output
    assert "Worker  2:" in result.output


def test_cli_prints_work_units_mode_when_requested(tmp_path, monkeypatch):
    _setup_single_commit_repo(tmp_path, monkeypatch)
    _install_fake_ai_provider(monkeypatch)

    result = _invoke_cli(tmp_path, ["--overall-progress-mode", "work-units"])

    assert result.exit_code == 0
    assert "Overall progress mode: work-units" in result.output


def test_cli_reports_when_no_summaries_need_generation(tmp_path, monkeypatch):
    _setup_single_commit_repo(
        tmp_path,
        monkeypatch,
        notes_by_commit={
            "a1b2c3d4": "Category: Added\n\nAdded summary already exists."
        },
    )
    _install_fake_ai_provider(monkeypatch, fail_on_summarize=True)

    result = _invoke_cli(tmp_path, [])

    assert result.exit_code == 0
    assert (
        "No AI summaries to generate: all processable commits already have notes"
        in result.output
    )
    assert (
        "No notes were updated in this run; continuing with changelog "
        "finalization from existing notes" in result.output
    )
    assert "Finalizing release metadata and changelog..." in result.output
    assert "Finalization" in result.output


def test_cli_noop_finalization_skips_ai_entry_generation_and_diff_reads(
    tmp_path, monkeypatch
):
    repo = _setup_single_commit_repo(
        tmp_path,
        monkeypatch,
        notes_by_commit={
            "a1b2c3d4": "Category: Added\n\nAdded summary already exists."
        },
    )

    def fail_get_commit_diff(commit):
        raise AssertionError("get_commit_diff should not be called")

    repo.get_commit_diff = fail_get_commit_diff
    _install_fake_ai_provider(monkeypatch, fail_on_generate_entry=True)

    result = _invoke_cli(tmp_path, [])

    assert result.exit_code == 0
    assert "Changelog" in result.output


def test_per_worker_progress_redraws_in_interactive_tty(monkeypatch):
    prepared = [
        _build_prepared_commit("a", "A", "feat: a", "+a"),
        _build_prepared_commit("b", "B", "feat: b", "+b"),
    ]

    results, output_chunks = _run_summary_generation_with_output_capture(
        monkeypatch,
        is_tty=True,
        prepared=prepared,
        workers=2,
    )

    assert len(results) == 2
    assert any("\x1b[" in chunk for chunk in output_chunks)


def test_per_worker_progress_appends_in_non_interactive_output(monkeypatch):
    prepared = [_build_prepared_commit("a", "A", "feat: a", "+a")]

    results, output_chunks = _run_summary_generation_with_output_capture(
        monkeypatch,
        is_tty=False,
        prepared=prepared,
        workers=1,
    )

    assert len(results) == 1
    assert not any("\x1b[" in chunk for chunk in output_chunks)


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
            committed_datetime=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        SimpleNamespace(
            hexsha="b2",
            message="docs: update readme",
            committed_datetime=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        SimpleNamespace(
            hexsha="c3",
            message="fix(api): handle edge case",
            committed_datetime=datetime(2026, 1, 3, tzinfo=UTC),
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


def test_create_semver_tags_if_needed_skips_already_tagged_commits():
    # Commit 'abc' already has tag v2.3.4, commit 'a1' has a note but no tag.
    # New tag should be bumped from highest existing (v2.3.4 -> v2.4.0 for Added).
    repo = DummyTagRepo(
        tags_by_commit={"abc": ["v2.3.4"]},
        notes_by_commit={"a1": "Category: Added\n\nNew feature."},
    )
    commits = [
        SimpleNamespace(
            hexsha="abc",
            message="fix: prior fix",
            committed_datetime=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        SimpleNamespace(
            hexsha="a1",
            message="feat(api): add endpoint",
            committed_datetime=datetime(2026, 1, 2, tzinfo=UTC),
        ),
    ]

    created = main._create_semver_tags_if_needed(
        repo, commits, "ai-changelog", True, None
    )

    assert created == 1
    assert repo.created_tags == [("v2.4.0", "a1")]


def test_create_semver_tags_if_needed_skips_when_no_new_noted_commits():
    # All noted commits already have tags; nothing new to tag.
    repo = DummyTagRepo(
        tags_by_commit={"abc": ["v2.3.4"]},
        notes_by_commit={"abc": "Category: Fixed\n\nFixed bug."},
    )
    commits = [
        SimpleNamespace(
            hexsha="abc",
            message="fix: prior fix",
            committed_datetime=datetime(2026, 1, 1, tzinfo=UTC),
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
        "- Old entry\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Refreshed entry\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert "## [1.1.0] - 2026-02-01" in merged
    assert "- New feature" in merged
    assert "- Old entry" in merged
    assert "- Refreshed entry" not in merged
    assert "## [1.1.0] - 2026-02-01" in merged
    assert merged.index("## [Unreleased]") < merged.index("## [1.1.0] - 2026-02-01")
    assert merged.index("## [1.1.0] - 2026-02-01") < merged.index("## [1.0.0]")


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


def test_merge_missing_release_sections_skips_existing_version_with_different_date():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-08-04\n\n"
        "### Added\n"
        "- Existing note\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-08-06\n\n"
        "### Added\n"
        "- Regenerated note\n\n"
        "## [1.3.0] - 2026-08-06\n\n"
        "### Changed\n"
        "- Newer release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert merged.count("## [1.2.0]") == 1
    assert "- Existing note" in merged
    assert "- Regenerated note" not in merged
    assert "## [1.3.0] - 2026-08-06" in merged


def test_merge_missing_release_sections_inserts_after_unreleased_with_md024_marker():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "<!-- Markdownlint-disable MD024 -->\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Placeholder\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert merged.index("<!-- Markdownlint-disable MD024 -->") < merged.index(
        "## [Unreleased]"
    )
    assert merged.index("## [Unreleased]") < merged.index("## [1.1.0] - 2026-02-01")
    assert merged.index("## [1.1.0] - 2026-02-01") < merged.index("## [1.0.0]")


def test_merge_missing_release_sections_creates_unreleased_when_missing():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "<!-- Markdownlint-disable MD024 -->\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert "## [Unreleased]" in merged
    assert merged.index("<!-- Markdownlint-disable MD024 -->") < merged.index(
        "## [Unreleased]"
    )
    assert merged.index("## [Unreleased]") < merged.index("## [1.1.0] - 2026-02-01")
    assert merged.index("## [1.1.0] - 2026-02-01") < merged.index("## [1.0.0]")


def test_merge_missing_release_sections_inserts_unreleased_even_without_new_sections():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "<!-- Markdownlint-disable MD024 -->\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )
    generated = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Initial release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 0
    assert "## [Unreleased]" in merged
    assert merged.index("<!-- Markdownlint-disable MD024 -->") < merged.index(
        "## [Unreleased]"
    )
    assert merged.index("## [Unreleased]") < merged.index("## [1.0.0]")


def test_merge_missing_release_sections_reorders_and_dedupes_existing_sections():
    existing = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "<!-- Markdownlint-disable MD024 -->\n\n"
        "## [1.2.0] - 2026-08-06\n\n"
        "### Added\n"
        "- New placement but wrong location\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-08-04\n\n"
        "### Added\n"
        "- Older duplicate\n\n"
        "## [1.1.0] - 2026-08-01\n\n"
        "### Added\n"
        "- Prior release\n"
    )
    generated = existing

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 0
    assert merged.index("## [Unreleased]") < merged.index("## [1.2.0]")
    assert merged.count("## [1.2.0]") == 1
    assert "- Older duplicate" not in merged
    assert "- New placement but wrong location" in merged


def test_merge_missing_release_sections_skips_versions_older_than_max_existing():
    # Simulates hand-written CHANGELOG with milestone versions (1.0.0) while the
    # generated changelog also contains finer per-commit tags (0.9.x) from before.
    existing = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-10\n\n"
        "### Added\n"
        "- Milestone release\n"
    )
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Added\n"
        "- New feature\n\n"
        "## [1.0.0] - 2026-01-10\n\n"
        "### Added\n"
        "- Milestone release\n\n"
        "## [0.9.1] - 2026-01-05\n\n"
        "### Fixed\n"
        "- Old per-commit fix tag\n\n"
        "## [0.9.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Old per-commit add tag\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 1
    assert "## [1.1.0]" in merged
    assert "## [0.9.1]" not in merged
    assert "## [0.9.0]" not in merged


def test_ensure_markdownlint_md024_disable_prepends_when_missing():
    text = "# Changelog\n\n## [Unreleased]\n"

    updated, inserted = main._ensure_markdownlint_md024_disable(text)

    assert inserted is True
    assert updated.startswith("<!-- Markdownlint-disable MD024 -->\n\n# Changelog")


def test_ensure_markdownlint_md024_disable_noop_when_present():
    text = "<!-- Markdownlint-disable MD024 -->\n\n# Changelog\n"

    updated, inserted = main._ensure_markdownlint_md024_disable(text)

    assert inserted is False
    assert updated == text


def test_cli_skips_existing_notes_and_writes_changelog(tmp_path, monkeypatch):
    commits = [
        _build_commit(
            "a1b2c3d4",
            "feat(cli): add changelog output",
            datetime(2026, 3, 1, tzinfo=UTC),
            "Alice",
        ),
        _build_commit(
            "b2c3d4e5",
            "fix(cli): handle legacy note",
            datetime(2026, 3, 2, tzinfo=UTC),
            "Bob",
        ),
    ]
    repo = _build_processing_repo(
        tmp_path,
        commits=commits,
        notes_by_commit={"b2c3d4e5": "Legacy summary without category."},
        diff_by_commit={
            "a1b2c3d4": "+new line",
            "b2c3d4e5": "-old line\n+new line",
        },
    )

    _patch_processing_repo(monkeypatch, repo)

    class FakeAIProvider:
        def __init__(self, config):
            self.config = config

        def summarize_diff(self, commit_message, diff, author=None):
            return f"Added summary for {commit_message.split(':', 1)[0]}."

        def generate_changelog_entry(self, commit_message, note, category, is_breaking):
            return note.splitlines()[0] if note else commit_message

    monkeypatch.setattr(main, "AIProvider", FakeAIProvider)

    result = _invoke_cli(
        tmp_path,
        ["--create-semver-tags", "--changelog-file", "CHANGELOG.md"],
    )

    assert result.exit_code == 0
    assert any("Category: Added" in note for _, note, _ in repo.saved_notes)
    assert not any("Category: Fixed" in note for _, note, _ in repo.saved_notes)
    assert repo.created_tags == [("v1.0.0", "a1b2c3d4")]
    changelog_text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.0.0] - 2026-03-01" in changelog_text


def test_cli_reports_no_commits_and_exits(tmp_path, monkeypatch):
    repo = _build_processing_repo(tmp_path, commits=[])
    _patch_processing_repo(monkeypatch, repo)
    _install_fake_ai_provider(monkeypatch)

    result = _invoke_cli(tmp_path, [])

    assert result.exit_code == 0
    assert "No commits found in repository" in result.output


# ---------------------------------------------------------------------------
# Tests for internal helper functions targeting specific surviving mutations
# ---------------------------------------------------------------------------


def test_resolve_worker_count_returns_one_for_zero_items(monkeypatch):
    """item_count=0 must return 1, not any other value (mutmut_1/3)."""
    monkeypatch.setattr(main.os, "cpu_count", lambda: 8)

    assert main._resolve_worker_count(None, 0) == 1
    assert main._resolve_worker_count(4, 0) == 1


def test_resolve_worker_count_caps_at_item_count():
    """Worker count may not exceed item_count."""
    assert main._resolve_worker_count(10, 3) == 3


def test_commit_message_str_decodes_bytes():
    """Bytes commit messages must be decoded as UTF-8 with error replacement."""
    msg = b"feat: add support for caf\xc3\xa9"  # codespell:ignore
    result = main._commit_message_str(msg)
    assert result == "feat: add support for café"


def test_commit_message_str_passes_string_through():
    """String inputs are returned unchanged."""
    assert main._commit_message_str("fix: typo") == "fix: typo"


def test_commit_message_str_handles_bytes_with_replacement():
    """Invalid byte sequences are replaced, not raised."""
    result = main._commit_message_str(b"bad byte: \xff")
    assert isinstance(result, str)
    assert "bad byte:" in result


def test_render_worker_progress_bar_with_total_zero():
    """A total of zero should return a full bar, not a partial bar."""
    result = main._render_worker_progress_bar(0, 0, width=4)
    assert result == "[####]"


def test_render_worker_progress_bar_with_total_one():
    """A total of exactly 1 must not behave the same as a zero total (mutmut_3)."""
    partial = main._render_worker_progress_bar(0, 1, width=4)
    full = main._render_worker_progress_bar(1, 1, width=4)
    # Partial bar for 0/1 should have at least one '-'
    assert "-" in partial
    assert full == "[####]"


def test_build_execution_command_includes_create_semver_tags():
    """--create-semver-tags flag must appear in the command string."""
    cmd = main._build_execution_command(
        repo_path="/repo",
        model="gpt-4o",
        namespace="ai-changelog",
        force=False,
        clear_all=False,
        create_semver_tags=True,
        limit=None,
        log_level="INFO",
        changelog_file="CHANGELOG.md",
        litellm_api_base=None,
        litellm_api_key=None,
        litellm_headers_json=None,
    )
    assert "--create-semver-tags" in cmd


def test_configure_logging_silences_third_party_loggers_above_debug():
    """Third-party loggers must be silenced when log level is above DEBUG."""
    main._configure_logging("INFO")
    httpx_logger = logging.getLogger("httpx")
    httpcore_logger = logging.getLogger("httpcore")
    litellm_logger = logging.getLogger("LiteLLM")

    assert httpx_logger.level == logging.WARNING
    assert httpcore_logger.level == logging.WARNING
    assert litellm_logger.level == logging.WARNING


def test_configure_logging_does_not_silence_at_debug_level():
    """At DEBUG level the application should not suppress third-party logs."""
    # Reset levels first
    logging.getLogger("httpx").setLevel(logging.NOTSET)
    main._configure_logging("DEBUG")
    # httpx should not be forced to WARNING
    assert logging.getLogger("httpx").level != logging.WARNING


def test_generate_summary_for_commit_uses_author_name(monkeypatch):
    """Author name from commit.author.name is forwarded to summarize_diff."""
    captured = {}

    class FakeProvider:
        def summarize_diff(self, commit_message, diff, author=None):
            captured["author"] = author
            return "Summary."

    prepared = main._PreparedCommit(
        commit=SimpleNamespace(
            hexsha="abc123",
            author=SimpleNamespace(name="Carol"),
        ),
        commit_message="feat: something",
        category="Added",
        existing_note=None,
        diff="+line",
    )

    result = main._generate_summary_for_commit(
        cast(main.AIProvider, FakeProvider()), prepared
    )

    assert result.commit_hash == "abc123"
    assert result.summary == "Summary."
    assert captured["author"] == "Carol"


def test_generate_summary_for_commit_handles_missing_author():
    """Commits without author attribute yield author=None in summarize_diff."""
    captured = {}

    class FakeProvider:
        def summarize_diff(self, commit_message, diff, author=None):
            captured["author"] = author
            return "Summary."

    prepared = main._PreparedCommit(
        commit=SimpleNamespace(hexsha="def456"),  # no .author attribute
        commit_message="fix: bug",
        category="Fixed",
        existing_note=None,
        diff="-old",
    )

    result = main._generate_summary_for_commit(
        cast(main.AIProvider, FakeProvider()), prepared
    )

    assert result.summary == "Summary."
    assert captured["author"] is None


def test_generate_summaries_concurrently_returns_empty_dict_for_no_commits():
    """Empty input must produce an empty result without errors."""

    class FakeProvider:
        def summarize_diff(self, *a, **kw):
            return "ok"

    result = main._generate_summaries_concurrently(
        cast(main.AIProvider, FakeProvider()), [], 2
    )
    assert result == {}


def test_generate_summaries_concurrently_increments_completed_by_one(monkeypatch):
    """Each completed future must increment its worker's count by exactly 1."""
    on_completed_calls = {"n": 0}

    class FakeProvider:
        def summarize_diff(self, *a, **kw):
            return "ok"

    monkeypatch.setattr(main.sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(main.click, "echo", lambda *a, **kw: None)

    prepared = [
        _build_prepared_commit(f"hash{i}", "X", "feat: x", "+x") for i in range(3)
    ]

    def capture_count():
        on_completed_calls["n"] += 1

    results = main._generate_summaries_concurrently(
        cast(main.AIProvider, FakeProvider()),
        prepared,
        workers=1,
        on_summary_completed=capture_count,
    )

    assert len(results) == 3
    assert on_completed_calls["n"] == 3


def test_normalize_release_sections_rstrips_before_joining():
    """Rebuilt sections must use rstrip to remove trailing newlines."""
    text = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- Entry\n\n\n"
    )

    result = main._normalize_release_sections(text)

    # Trailing whitespace within sections should not cause double blank lines
    assert "\n\n\n" not in result


def test_ensure_unreleased_and_get_insertion_index_creates_header_for_empty_input():
    """Empty text must produce exactly '## [Unreleased]\\n\\n'."""
    updated, index = main._ensure_unreleased_and_get_insertion_index("")

    assert updated == "## [Unreleased]\n\n"
    assert index == len(updated)


def test_ensure_unreleased_and_get_insertion_index_inserts_before_first_semver():
    """When no Unreleased exists, inserts one before the first semantic release."""
    text = "## [1.0.0] - 2026-01-01\n\n### Added\n- First\n"

    updated, index = main._ensure_unreleased_and_get_insertion_index(text)

    assert "## [Unreleased]" in updated
    assert updated.index("## [Unreleased]") < updated.index("## [1.0.0]")
    # Insertion point must fall after the Unreleased section
    assert updated[index:].startswith("## [1.0.0]")


def test_merge_missing_release_sections_separator_between_blocks():
    """New sections must be separated by double newline, not arbitrary text."""
    existing = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- First release\n"
    )
    generated = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-03-01\n\n"
        "### Added\n"
        "- New version\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "### Fixed\n"
        "- A fix\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "### Added\n"
        "- First release\n"
    )

    merged, added = main._merge_missing_release_sections(existing, generated)

    assert added == 2
    # Both new sections present with correct double-newline separation
    assert "## [1.2.0]" in merged
    assert "## [1.1.0]" in merged
    idx_12 = merged.index("## [1.2.0]")
    idx_11 = merged.index("## [1.1.0]")
    separator = merged[idx_12:idx_11]
    assert "\n\n" in separator
