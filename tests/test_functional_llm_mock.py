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

"""Functional tests for CLI execution with an external mock LLM provider."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from git import Repo

from ai_changelog_msg.git_helper import GitRepository
from ai_changelog_msg.main import cli

pytestmark = pytest.mark.integration


def _init_git_repo_with_commit(repo_path: Path) -> str:
    """Initialize a git repository with one commit and return its SHA."""
    repo = Repo.init(repo_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "AI Changelog Test")
        writer.set_value("user", "email", "ai-changelog-test@example.com")
    file_path = repo_path / "README.md"
    file_path.write_text("# Functional Test\n\nInitial content.\n", encoding="utf-8")
    repo.index.add([str(file_path)])
    commit = repo.index.commit("feat: add initial project readme")
    return commit.hexsha


def test_cli_generates_note_with_llm_mock_provider(tmp_path: Path) -> None:
    """Run the CLI against a live mock LLM endpoint and persist a git note."""
    if os.getenv("CHANGELOG_FUNCTIONAL_LLM_MOCK") != "1":
        pytest.skip("Set CHANGELOG_FUNCTIONAL_LLM_MOCK=1 to run LLMock functional test")

    llm_mock_base_url = os.getenv("LLM_MOCK_BASE_URL", "http://127.0.0.1:8001/chatgpt")
    commit_hash = _init_git_repo_with_commit(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(tmp_path),
            "--model",
            "openai/gpt-4o-mini",
            "--namespace",
            "functional-llm-mock",
            "--workers",
            "1",
            "--litellm-api-base",
            llm_mock_base_url,
            "--litellm-api-key",
            "mock-api-key",
            "--changelog-file",
            "CHANGELOG.generated.md",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Processing complete" in result.output
    assert "Changelog written to:" in result.output
    assert "Token usage:" in result.output

    repo = GitRepository(str(tmp_path))
    generated_note = repo.get_note(commit_hash, "functional-llm-mock")
    assert generated_note is not None
    assert generated_note.strip()
    assert (tmp_path / "CHANGELOG.generated.md").exists()


def test_cli_skips_ai_generation_when_note_already_exists(tmp_path: Path) -> None:
    """CLI should skip AI summary generation when the commit already has a note."""
    commit_hash = _init_git_repo_with_commit(tmp_path)
    repo = GitRepository(str(tmp_path))
    repo.set_note(
        commit_hash,
        "Category: Added\nSummary: pre-seeded note",
        "functional-preseeded",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(tmp_path),
            "--namespace",
            "functional-preseeded",
            "--workers",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "No AI summaries to generate" in result.output
    assert "No notes were updated in this run" in result.output
    assert repo.get_note(commit_hash, "functional-preseeded") is not None


def test_cli_clear_all_reports_when_namespace_is_empty(tmp_path: Path) -> None:
    """clear-all should report when no notes exist in the selected namespace."""
    _init_git_repo_with_commit(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(tmp_path),
            "--namespace",
            "functional-empty-namespace",
            "--clear-all",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (
        "No git notes found for namespace: functional-empty-namespace" in result.output
    )


def test_cli_clear_all_removes_existing_notes(tmp_path: Path) -> None:
    """clear-all should remove previously created notes in the selected namespace."""
    commit_hash = _init_git_repo_with_commit(tmp_path)
    repo = GitRepository(str(tmp_path))
    repo.set_note(
        commit_hash, "Category: Added\nSummary: test note", "functional-clear"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(tmp_path),
            "--namespace",
            "functional-clear",
            "--clear-all",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Removed all git notes from namespace: functional-clear" in result.output
    assert repo.get_note(commit_hash, "functional-clear") is None
