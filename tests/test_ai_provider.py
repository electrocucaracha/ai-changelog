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
