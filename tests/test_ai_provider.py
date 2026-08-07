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

import logging
from io import BytesIO
from types import SimpleNamespace

import pytest

from ai_changelog_msg import ai_provider
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
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        raise ValueError("boom")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    with pytest.raises(RuntimeError, match="AI API call failed: boom"):
        provider.summarize_diff("fix: issue", "+change")
    assert calls["count"] == 1


def test_summarize_diff_retries_timeout_and_succeeds(monkeypatch):
    calls = {"count": 0}
    observed_delays = []

    def fake_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError(
                "litellm.APIConnectionError: OllamaException - litellm.Timeout: "
                "Connection timed out after 600.0 seconds."
            )
        return _make_response("Recovered after retry.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    def _record_delay(delay: float) -> None:
        observed_delays.append(delay)

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.time.sleep",
        _record_delay,
    )

    provider = AIProvider(Config())
    summary = provider.summarize_diff("feat: reduce timeout flakiness", "+change")

    assert summary == "Recovered after retry."
    assert calls["count"] == 3
    assert observed_delays == [1.0, 2.0]


def test_summarize_diff_pulls_missing_ollama_model_then_retries(monkeypatch):
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("model 'llama3.1:8b-instruct-q4_K_M' not found")
        return _make_response("Recovered after pull.")

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status":"success"}'

    def fake_urlopen(*args, **kwargs):
        return _Response()

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(Config(model="ollama/llama3.1:8b-instruct-q4_K_M"))
    summary = provider.summarize_diff("feat: improve defaults", "+change")

    assert summary == "Recovered after pull."
    assert calls["count"] == 2


def test_summarize_diff_raises_when_ollama_pull_fails(monkeypatch):
    def fake_completion(**kwargs):
        raise ValueError("model 'llama3.1:8b-instruct-q4_K_M' not found")

    def fake_urlopen(*args, **kwargs):
        raise ai_provider.urllib_error.HTTPError(
            url="http://localhost:11434/api/pull",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=BytesIO(
                b"pull access denied for llama3.1:8b-instruct-q4_K_M"  # gitleaks:allow
            ),
        )

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(Config(model="ollama/llama3.1:8b-instruct-q4_K_M"))

    with pytest.raises(RuntimeError, match="Failed to pull Ollama model"):
        provider.summarize_diff("feat: improve defaults", "+change")


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


def test_generate_changelog_entry_rejects_prompt_leak_and_falls_back(monkeypatch):
    def fake_completion(**kwargs):
        return _make_response(
            "### System: You normalize engineering summaries into one uniform "
            "Keep a Changelog entry sentence written for a technical audience."
        )

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    result = provider.generate_changelog_entry(
        "chore: adjust workflow",
        "Refined workflow behavior for maintainers.",
        "Changed",
        False,
    )

    assert result == "Refined workflow behavior for maintainers."


def test_generate_changelog_entry_returns_first_valid_sentence(monkeypatch):
    def fake_completion(**kwargs):
        return _make_response(
            "- Streamlined dependency updates for operators. "
            "Additional implementation details are intentionally omitted."
        )

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    result = provider.generate_changelog_entry(
        "chore: adjust dependency workflow",
        "Adjusted dependency workflow.",
        "Changed",
        False,
    )

    assert result == "Streamlined dependency updates for operators."


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


def test_init_enables_headroom_callback_once(monkeypatch):
    class FakeHeadroomCallback:
        pass

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider._HeadroomCallback",
        FakeHeadroomCallback,
    )
    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.callbacks", [])

    AIProvider(Config(enable_headroom=True))
    AIProvider(Config(enable_headroom=True))

    callbacks = [
        callback
        for callback in ai_provider.litellm.callbacks
        if callback.__class__.__name__ == "FakeHeadroomCallback"
    ]
    assert len(callbacks) == 1


def test_init_raises_when_headroom_enabled_but_not_installed(monkeypatch):
    monkeypatch.setattr("ai_changelog_msg.ai_provider._HeadroomCallback", None)

    with pytest.raises(RuntimeError, match="Headroom is enabled but not installed"):
        AIProvider(Config(enable_headroom=True))


def test_init_sets_litellm_num_retries_to_zero(monkeypatch):
    """litellm.num_retries must be set to 0 to disable LiteLLM's own retry loop."""
    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.num_retries", 999)

    AIProvider(Config())

    assert ai_provider.litellm.num_retries == 0


def test_init_suppresses_litellm_loggers(monkeypatch):
    """Both 'litellm' and 'LiteLLM' loggers must be set to WARNING level."""
    AIProvider(Config())

    assert logging.getLogger("litellm").level == logging.WARNING
    assert logging.getLogger("LiteLLM").level == logging.WARNING


def test_init_sets_suppress_debug_info_when_available(monkeypatch):
    """litellm.suppress_debug_info must be set to True when the attribute exists."""
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.suppress_debug_info", False
    )

    AIProvider(Config())

    assert ai_provider.litellm.suppress_debug_info is True


def test_init_logs_provider_details(caplog):
    """Init must log model, timeout, retries, and backoff at DEBUG level."""
    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.ai_provider"):
        AIProvider(Config(model="test-model", retry_attempts=5))

    init_records = [r for r in caplog.records if "initialised" in r.getMessage()]
    assert init_records, "Expected AIProvider initialised debug log"
    msg = init_records[0].getMessage()
    assert "test-model" in msg
    assert "5" in msg


def test_summarize_diff_sends_correct_completion_params(monkeypatch):
    """Verify max_tokens, temperature, role key, and system prompt content."""
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _make_response("Summary.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())
    provider.summarize_diff("feat: add feature", "+new code")

    assert captured["max_tokens"] == 500
    assert captured["temperature"] == 0.3
    assert captured["model"] == provider.model
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["role"] == "user"
    system_content = captured["messages"][0]["content"]
    assert system_content.startswith("You write concise git-note summaries")
    assert "Ignore minor refactors" in system_content
    assert "typically at most 80 words" in system_content
    assert "Preserve this priority order when condensing" in system_content
    assert "primary user or maintainer outcome" in system_content
    assert "must state what changed" in system_content
    assert "matters to users or maintainers" in system_content
    assert "copying from the commit message or diff" in system_content
    assert "2 to 4 sentences" in system_content
    # Adjacent-boundary checks to detect 'XX' insertion and case mutations
    assert "analysis. Output plain text only" in system_content
    assert "sentences and typically at most 80 words" in system_content
    assert "condensing: (1) breaking behavior" in system_content
    assert "outcome. The first sentence" in system_content
    assert "changed and why it matters" in system_content
    assert "direct copying from the commit message" in system_content
    assert "'Optional additional context'. Always mention breaking" in system_content
    assert "present. Never mention file paths" in system_content
    assert "security impact when present. Never" in system_content


def test_generate_changelog_entry_sends_correct_completion_params(monkeypatch):
    """Verify max_tokens, temperature, and system prompt for changelog entry."""
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _make_response("Streamlined the CLI workflow.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())
    provider.generate_changelog_entry(
        "chore: update workflow",
        "Updated the workflow for operators.",
        "Changed",
        False,
    )

    assert captured["max_tokens"] == 120
    assert captured["temperature"] == 0.35
    system_content = captured["messages"][0]["content"]
    assert "normalize engineering summaries" in system_content
    assert "but do not start with literal labels Added" in system_content
    assert "for developers or operators" in system_content
    user_content = captured["messages"][1]["content"]
    assert "state that clearly in one sentence" in user_content
    assert "enabled, introduced, optimized" in user_content


def test_build_prompt_includes_numbered_checklist_items():
    """Numbered checklist items must appear with adjacent boundaries intact."""
    provider = AIProvider.__new__(AIProvider)

    prompt = provider._build_prompt("fix: correct output", "+fix", "Alice")

    # Use adjacent-boundary checks to detect 'XX' insertion mutations
    assert "minor edits. (3) Write in your own words" in prompt
    assert "CLI changes, security impact, config schema" in prompt
    assert "(5) Output exactly one paragraph of 2 to 4 sentences" in prompt
    assert "(6) Start with what changed and why it matters." in prompt
    assert "'Optional additional context'." in prompt
    assert isinstance(prompt, str)
    # Verify join separator doesn't get corrupted
    assert "Author: Alice\n\nOriginal Commit Message:" in prompt


def test_sanitize_changelog_entry_continues_past_empty_lines():
    """Empty lines must be skipped (continue), not abort processing (break)."""
    provider = AIProvider.__new__(AIProvider)

    # An empty line in the middle should NOT stop collection of further lines.
    # With 'break', second part would be ignored and the merged text would be
    # just "First part", producing result "First part".
    # With 'continue', second part is collected and merged = "First part Second part."
    content = "First part\n\nSecond part completes the thought."
    result = provider._sanitize_changelog_entry(content)

    # The full merged text (both parts joined) must be used for the result
    assert result is not None
    assert "Second part" in result


def test_sanitize_changelog_entry_removes_leading_quotes():
    """Leading and trailing quote characters must be stripped, not replaced."""
    provider = AIProvider.__new__(AIProvider)

    result = provider._sanitize_changelog_entry('"Enabled the new feature."')

    assert result == "Enabled the new feature."
    assert "XXXX" not in (result or "")


def test_completion_with_retry_stops_after_exact_max_attempts(monkeypatch):
    """Verify retry stops at _max_completion_attempts, not one more."""
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        raise ValueError("timeout")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )
    monkeypatch.setattr("ai_changelog_msg.ai_provider.time.sleep", lambda _: None)

    provider = AIProvider(Config(retry_attempts=3))

    with pytest.raises(RuntimeError):
        provider.summarize_diff("feat: test", "+change")

    # Exactly max_completion_attempts calls, not max_completion_attempts + 1
    assert calls["count"] == 3


def test_summarize_diff_returns_placeholder_when_model_returns_empty(monkeypatch):
    """Verify placeholder is returned when model produces no content."""

    def fake_completion(**kwargs):
        return _make_response(None)

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())
    result = provider.summarize_diff("fix: typo", "+tiny fix")

    assert result == "[Failed to generate summary]"


def test_summarize_diff_logs_truncation_message(monkeypatch, caplog):
    """Truncation debug log must include meaningful format string and args."""

    def fake_completion(**kwargs):
        return _make_response("Summary.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config(max_diff_size=5))
    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.ai_provider"):
        provider.summarize_diff("feat: test", "abcdefghij")

    assert "Truncating diff" in caplog.text
    assert "10" in caplog.text


def test_summarize_diff_logs_model_name_in_request_message(monkeypatch, caplog):
    """The 'Sending request' debug log must include the model name, not None."""

    def fake_completion(**kwargs):
        return _make_response("Summary.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config(model="gpt-4o-test"))
    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.ai_provider"):
        provider.summarize_diff("feat: test", "+change")

    # Verify the 'Sending request' log uses the actual model name, not None
    request_log_records = [
        r for r in caplog.records if "Sending request to model" in r.getMessage()
    ]
    assert request_log_records, "Expected 'Sending request' debug log not found"
    assert "gpt-4o-test" in request_log_records[0].getMessage()
    # Must use lowercase format string (not mutated to uppercase)
    assert "SENDING REQUEST" not in caplog.text
