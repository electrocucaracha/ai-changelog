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

from types import SimpleNamespace

import pytest

from ai_changelog_msg.ai_provider import AIProvider
from ai_changelog_msg.config import Config


def _make_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_summarize_diff_truncates_and_returns_trimmed_content(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _make_response("  Added support for summaries.  ")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config(max_diff_size=5))

    summary = provider.summarize_diff("feat: add feature", "abcdefghi", "Alice")

    assert summary == "Added support for summaries."
    prompt = captured["messages"][1]["content"]
    assert "Author: Alice" in prompt
    assert "... (truncated, 4 more characters)" in prompt


def test_summarize_diff_raises_runtime_error_on_api_failure(monkeypatch):
    def fake_completion(**kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    with pytest.raises(RuntimeError, match="AI API call failed: boom"):
        provider.summarize_diff("fix: issue", "+change")


def test_generate_changelog_entry_returns_ai_content(monkeypatch):
    def fake_completion(**kwargs):
        return _make_response("Changed the CLI workflow.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    result = provider.generate_changelog_entry(
        "chore: adjust workflow",
        "Changed the CLI workflow with internal refactoring.",
        "Changed",
        False,
    )

    assert result == "Changed the CLI workflow."


def test_generate_changelog_entry_falls_back_to_note_on_failure(monkeypatch):
    def fake_completion(**kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    result = provider.generate_changelog_entry(
        "docs: refresh readme",
        "Refreshed README details.",
        "Changed",
        False,
    )

    assert result == "Refreshed README details."


def test_summarize_diff_passes_litellm_gateway_kwargs(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _make_response("Added gateway support.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(
        Config(
            litellm_api_base="https://gateway.example",
            litellm_api_key="token",
            litellm_extra_headers={"X-Org": "platform"},
        )
    )

    result = provider.summarize_diff("feat: add support", "+new behavior")

    assert result == "Added gateway support."
    assert captured["api_base"] == "https://gateway.example"
    assert captured["api_key"] == "token"
    assert captured["extra_headers"] == {"X-Org": "platform"}


def test_summarize_diff_includes_pr_author_and_approver_when_present(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _make_response("Streamlined release note quality.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    commit_message = (
        "Merge pull request #42 from octocat/feature\n\n"
        "feat: improve changelog context\n\n"
        "Reviewed-by: Jane Reviewer <jane@example.com>\n"
        "Approved-by: John Approver <john@example.com>"
    )
    provider.summarize_diff(commit_message, "+new behavior", "Alice")

    prompt = captured["messages"][1]["content"]
    assert "Author: Alice" in prompt
    assert "PR Author: octocat" in prompt
    assert "Approver: Jane Reviewer, John Approver" in prompt


def test_build_prompt_includes_summarization_best_practices():
    provider = AIProvider(Config())

    prompt = provider._build_prompt(
        "feat: improve release note quality",
        "+ meaningful user-facing behavior change",
        "Alice",
    )

    assert "Summarization checklist:" in prompt
    assert "Identify the core thesis of the change." in prompt
    assert "Write in your own words with an objective tone." in prompt
    assert "Preserve critical details first" in prompt
    assert "breaking or migration requirements" in prompt
    assert "API or CLI" in prompt
    assert "security impact" in prompt
    assert "target 80 words unless critical details require slightly more" in prompt
    assert "Do not output headers or lead-ins" in prompt
    assert "Here is a summary" in prompt
    assert "Optional additional context" in prompt
