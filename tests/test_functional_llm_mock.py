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

# Ensure local mock calls bypass any proxy configuration for this test process,
# including libraries that read env vars during module import.
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from ai_changelog_msg.git_helper import GitRepository
from ai_changelog_msg.main import cli

pytestmark = pytest.mark.integration


def _init_git_repo_with_commit(repo_path: Path) -> str:
    """Initialize a git repository with one commit and return its SHA."""
    repo = Repo.init(repo_path)
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
