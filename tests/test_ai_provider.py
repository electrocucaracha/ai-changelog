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
from collections.abc import Callable
from io import BytesIO
from types import SimpleNamespace

import pytest

from ai_changelog_msg import ai_provider
from ai_changelog_msg.ai_provider import AIProvider
from ai_changelog_msg.config import Config

OLLAMA_MODEL_NAME = "llama3.1:8b-instruct-q4_K_M"
OLLAMA_MODEL = "ollama/" + OLLAMA_MODEL_NAME
OLLAMA_PULL_DENIED = "pull access denied for " + OLLAMA_MODEL_NAME


def _make_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


class _SuccessfulOllamaPullResponse:
    """HTTP response stub for successful Ollama model pull requests."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"status":"success"}'


def _fake_successful_ollama_urlopen(*args, **kwargs):
    """Return a successful response for mocked `urlopen` pull calls."""
    return _SuccessfulOllamaPullResponse()


def _configure_missing_ollama_model_then_recover(
    monkeypatch: pytest.MonkeyPatch,
    on_completion_call: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, int]:
    """Patch AI completion to fail once for missing model, then recover.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to patch dependencies.
        on_completion_call: Optional callback invoked with completion kwargs.

    Returns:
        A mutable call counter dict with key ``count``.
    """
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        if on_completion_call is not None:
            on_completion_call(kwargs)
        if calls["count"] == 1:
            raise ValueError(f"model '{OLLAMA_MODEL_NAME}' not found")
        return _make_response("Recovered after pull.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen",
        _fake_successful_ollama_urlopen,
    )
    return calls


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
    monkeypatch.setattr("ai_changelog_msg.ai_provider.time.sleep", lambda _: None)

    provider = AIProvider(Config())

    with pytest.raises(RuntimeError, match="AI API call failed: boom"):
        provider.summarize_diff("fix: issue", "+change")
    assert calls["count"] == 1


def test_summarize_diff_retries_timeout_and_succeeds(caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="ai_changelog_msg.ai_provider")
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
    assert any(
        record.getMessage()
        == (
            "Transient AI API error on attempt 1/3: litellm.APIConnectionError: "
            "OllamaException - litellm.Timeout: Connection timed out after 600.0 "
            "seconds.. Retrying in 1.0s"
        )
        for record in caplog.records
    )


def test_completion_with_ollama_auto_pull_forwards_max_tokens(monkeypatch):
    captured = {
        "max_tokens": [],
        "messages": [],
        "model": [],
        "temperature": [],
    }

    def _capture_kwargs(kwargs: dict[str, object]) -> None:
        captured["max_tokens"].append(kwargs["max_tokens"])
        captured["messages"].append(kwargs["messages"])
        captured["model"].append(kwargs["model"])
        captured["temperature"].append(kwargs["temperature"])

    calls = _configure_missing_ollama_model_then_recover(monkeypatch, _capture_kwargs)

    provider = AIProvider(Config(model=OLLAMA_MODEL))
    summary = provider.summarize_diff("feat: improve defaults", "+change")

    assert summary == "Recovered after pull."
    assert calls["count"] == 2
    assert captured["max_tokens"] == [500, 500]
    assert captured["messages"][0] == captured["messages"][1]
    assert captured["model"] == [provider.model, provider.model]
    assert captured["temperature"] == [0.3, 0.3]


def test_completion_with_ollama_auto_pull_forwards_gateway_kwargs_on_retry(monkeypatch):
    captured_kwargs: list[dict[str, object]] = []

    def _capture_kwargs(kwargs: dict[str, object]) -> None:
        captured_kwargs.append(kwargs)

    _configure_missing_ollama_model_then_recover(monkeypatch, _capture_kwargs)

    provider = AIProvider(
        Config(
            model=OLLAMA_MODEL,
            litellm_api_base="https://gateway.example",
            litellm_api_key="token",
            litellm_extra_headers={"X-Org": "platform"},
        )
    )
    summary = provider.summarize_diff("feat: improve defaults", "+change")

    assert summary == "Recovered after pull."
    assert len(captured_kwargs) == 2
    for call_kwargs in captured_kwargs:
        assert call_kwargs["api_base"] == "https://gateway.example"
        assert call_kwargs["api_key"] == "token"
        assert call_kwargs["extra_headers"] == {"X-Org": "platform"}


def test_summarize_diff_pulls_missing_ollama_model_then_retries(monkeypatch):
    calls = _configure_missing_ollama_model_then_recover(monkeypatch)

    provider = AIProvider(Config(model=OLLAMA_MODEL))
    summary = provider.summarize_diff("feat: improve defaults", "+change")

    assert summary == "Recovered after pull."
    assert calls["count"] == 2


def test_summarize_diff_raises_when_ollama_pull_fails(monkeypatch):
    def fake_completion(**kwargs):
        raise ValueError(f"model '{OLLAMA_MODEL_NAME}' not found")

    def fake_urlopen(*args, **kwargs):
        raise ai_provider.urllib_error.HTTPError(
            url="http://localhost:11434/api/pull",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=BytesIO(OLLAMA_PULL_DENIED.encode("utf-8")),
        )

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(Config(model=OLLAMA_MODEL))

    with pytest.raises(RuntimeError, match="Failed to pull Ollama model"):
        provider.summarize_diff("feat: improve defaults", "+change")


def test_pull_ollama_model_uses_post_request_and_utf8_replace(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="ai_changelog_msg.ai_provider")
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"{\xff\xfe\xfd}"

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(
        Config(
            model=OLLAMA_MODEL, litellm_api_base="https://ollama.example:11434/api/v1"
        )
    )

    provider._pull_ollama_model()

    request = captured["request"]
    assert request.full_url.startswith("https://ollama.example:11434/api/pull")
    assert request.get_method() == "POST"
    assert request.data is not None
    assert request.headers["Content-type"] == "application/json"
    assert captured["timeout"] == provider.config.api_timeout
    assert any(
        record.getMessage()
        == f"Ollama model '{OLLAMA_MODEL_NAME}' not available locally; pulling"
        for record in caplog.records
    )


def test_pull_ollama_model_decodes_http_error_details_with_utf8_replace(monkeypatch):
    def fake_urlopen(request, timeout):
        raise ai_provider.urllib_error.HTTPError(
            url=request.full_url,
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=BytesIO(OLLAMA_PULL_DENIED.encode("utf-8") + b"\xff"),
        )

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(Config(model=OLLAMA_MODEL))

    with pytest.raises(RuntimeError, match=OLLAMA_PULL_DENIED):
        provider._pull_ollama_model()


def _patch_ollama_urlopen(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch urlopen with a fake that captures the request and returns success."""
    captured: dict = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status":"success"}'

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return _Response()

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )
    return captured


def test_pull_ollama_model_falls_back_to_localhost_for_malformed_api_base(monkeypatch):
    captured = _patch_ollama_urlopen(monkeypatch)

    provider = AIProvider(Config(model=OLLAMA_MODEL, litellm_api_base="http://"))

    provider._pull_ollama_model()

    assert captured["request"].full_url.startswith("http://localhost:11434/api/pull")


def test_pull_ollama_model_uses_default_localhost_base_when_not_configured(monkeypatch):
    captured = _patch_ollama_urlopen(monkeypatch)

    provider = AIProvider(Config(model=OLLAMA_MODEL, litellm_api_base=None))
    provider._pull_ollama_model()

    assert captured["request"].full_url == "http://localhost:11434/api/pull"


def test_pull_ollama_model_sends_correct_json_payload_with_name_key(monkeypatch):
    """Verify the JSON payload contains the 'name' key (not corrupted variants)."""
    import json as json_module

    captured = _patch_ollama_urlopen(monkeypatch)

    provider = AIProvider(Config(model=OLLAMA_MODEL))
    provider._pull_ollama_model()

    # Extract and parse the JSON payload
    payload_bytes = captured["request"].data
    assert payload_bytes is not None
    payload_dict = json_module.loads(payload_bytes.decode("utf-8"))

    # Verify the correct key is present and has the right value
    assert "name" in payload_dict
    assert payload_dict["name"] == OLLAMA_MODEL_NAME
    assert payload_dict["stream"] is False


def test_pull_ollama_model_detects_error_key_in_response(monkeypatch):
    """Verify the response error checking uses the 'error' key (not corrupted variants)."""
    import json as json_module

    class _ErrorResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json_module.dumps({"error": "model not available"}).encode("utf-8")

    def fake_urlopen(request, timeout):
        return _ErrorResponse()

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", fake_urlopen
    )

    provider = AIProvider(Config(model=OLLAMA_MODEL))

    with pytest.raises(
        RuntimeError, match="Failed to pull Ollama model.*model not available"
    ):
        provider._pull_ollama_model()


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


def test_generate_changelog_entry_falls_back_to_commit_message_when_note_blank(
    monkeypatch,
):
    def fake_completion(**kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    result = provider.generate_changelog_entry(
        "docs: refresh readme", "   ", "Changed", False
    )

    assert result == "docs: refresh readme"


def test_generate_changelog_entry_logs_fallback_reason(caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="ai_changelog_msg.ai_provider")

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
    assert any(
        record.getMessage() == "Falling back to note text for changelog entry: offline"
        for record in caplog.records
    )


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


def test_summarize_diff_logs_truncation_and_failure(caplog, monkeypatch):
    caplog.set_level(logging.DEBUG, logger="ai_changelog_msg.ai_provider")

    def fake_completion(**kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config(max_diff_size=4))

    with pytest.raises(RuntimeError, match="AI API call failed: offline"):
        provider.summarize_diff("feat: add support", "abcdefghi")

    messages = [record.getMessage() for record in caplog.records]
    assert "Truncating diff from 9 to 4 chars" in messages
    assert any(message.startswith("API call to '") for message in messages)


def test_summarize_diff_logs_model_response(caplog, monkeypatch):
    caplog.set_level(logging.DEBUG, logger="ai_changelog_msg.ai_provider")

    def fake_completion(**kwargs):
        return _make_response("Response content.")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.completion", fake_completion
    )

    provider = AIProvider(Config())

    summary = provider.summarize_diff("feat: add support", "+new line")

    assert summary == "Response content."
    assert any(
        record.getMessage() == f"Response received from model '{provider.model}'"
        for record in caplog.records
    )


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


def test_init_enables_headroom_callback_once(caplog, monkeypatch):
    class FakeHeadroomCallback:
        pass

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider._HeadroomCallback",
        FakeHeadroomCallback,
    )
    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.callbacks", [])

    caplog.set_level(logging.INFO, logger="ai_changelog_msg.ai_provider")

    AIProvider(Config(enable_headroom=True))
    AIProvider(Config(enable_headroom=True))

    callbacks = [
        callback
        for callback in ai_provider.litellm.callbacks
        if callback.__class__.__name__ == "FakeHeadroomCallback"
    ]
    assert len(callbacks) == 1
    assert any(
        record.getMessage() == "Headroom compression enabled for LiteLLM requests"
        for record in caplog.records
    )


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


def test_load_custom_providers_registers_discovered_provider(monkeypatch, caplog):
    """Entry-point providers must be loaded and added to custom_provider_map."""

    class FakeHandler:
        pass

    fake_ep = SimpleNamespace(name="my_provider", value="mypkg.llm:FakeHandler")
    fake_ep.load = lambda: FakeHandler

    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.custom_provider_map", [])

    def fake_entry_points(*, group):
        if group == "ai_changelog.litellm_providers":
            return [fake_ep]
        return []

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.entry_points",
        fake_entry_points,
        raising=False,
    )

    with caplog.at_level(logging.INFO, logger="ai_changelog_msg.ai_provider"):
        AIProvider(Config())

    registered = ai_provider.litellm.custom_provider_map
    assert any(
        entry["provider"] == "my_provider"
        and isinstance(entry["custom_handler"], FakeHandler)
        for entry in registered
    )
    assert any("my_provider" in r.getMessage() for r in caplog.records)


def test_load_custom_providers_is_idempotent(monkeypatch):
    """Calling AIProvider() twice must not register the same provider twice."""

    class FakeHandler:
        pass

    fake_ep = SimpleNamespace(name="my_provider", value="mypkg.llm:FakeHandler")
    fake_ep.load = lambda: FakeHandler

    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.custom_provider_map", [])

    def fake_entry_points(*, group):
        if group == "ai_changelog.litellm_providers":
            return [fake_ep]
        return []

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.entry_points",
        fake_entry_points,
        raising=False,
    )

    AIProvider(Config())
    AIProvider(Config())

    count = sum(
        1
        for entry in ai_provider.litellm.custom_provider_map
        if entry.get("provider") == "my_provider"
    )
    assert count == 1


def test_load_custom_providers_warns_on_load_failure(monkeypatch, caplog):
    """A broken entry point must log a warning and not raise."""

    fake_ep = SimpleNamespace(name="bad_provider", value="badpkg.llm:Bad")
    fake_ep.load = lambda: (_ for _ in ()).throw(ImportError("missing dep"))

    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.custom_provider_map", [])

    def fake_entry_points(*, group):
        if group == "ai_changelog.litellm_providers":
            return [fake_ep]
        return []

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.entry_points",
        fake_entry_points,
        raising=False,
    )

    with caplog.at_level(logging.WARNING, logger="ai_changelog_msg.ai_provider"):
        AIProvider(Config())  # must not raise

    assert any("bad_provider" in r.getMessage() for r in caplog.records)


def test_load_custom_providers_skips_when_no_entry_points(monkeypatch):
    """No custom_provider_map mutation when no providers are registered."""

    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.custom_provider_map", [])

    def fake_entry_points(*, group):
        return []

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.entry_points",
        fake_entry_points,
        raising=False,
    )

    AIProvider(Config())

    assert ai_provider.litellm.custom_provider_map == []


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


def test_extract_review_metadata_deduplicates_repeated_approver():
    """Duplicate approver identity must appear exactly once, not twice.

    Kills _extract_review_metadata mutmut_21: 'and identity not in approvers'
    changed to 'or identity not in approvers'. With 'or', a duplicate identity
    would be added again because the identity is truthy.
    """
    provider = AIProvider.__new__(AIProvider)
    commit_message = (
        "Merge pull request #10 from alice/feature\n\n"
        "feat: add feature\n\n"
        "Reviewed-by: Alice <alice@example.com>\n"
        "Approved-by: Alice <alice@example.com>\n"
    )

    _, approver = provider._extract_review_metadata(commit_message)

    assert approver == "Alice"


def test_init_headroom_preserves_existing_callbacks(monkeypatch):
    """Existing callbacks must be preserved when enabling Headroom.

    Kills _enable_headroom_compression_if_requested mutmut_10:
    getattr(litellm, 'callbacks', None) changed to getattr(litellm, 'CALLBACKS', None).
    With 'CALLBACKS', the existing list is not found (returns None), a new empty list
    is created, and the existing callback is lost.
    """

    class FakeHeadroomCallback:
        pass

    class ExistingCallback:
        pass

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider._HeadroomCallback",
        FakeHeadroomCallback,
    )
    existing = ExistingCallback()
    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.callbacks", [existing])

    AIProvider(Config(enable_headroom=True))

    callbacks = ai_provider.litellm.callbacks
    assert any(
        isinstance(c, ExistingCallback) for c in callbacks
    ), "Existing callback must be preserved"
    assert any(
        isinstance(c, FakeHeadroomCallback) for c in callbacks
    ), "Headroom callback must be appended"


def test_init_headroom_converts_non_list_callbacks_to_list(monkeypatch):
    """Non-list callbacks attribute must be converted to list before appending.

    Kills _enable_headroom_compression_if_requested mutmut_16:
    list(callbacks) changed to list(None), which would TypeError at runtime.
    """

    class FakeHeadroomCallback:
        pass

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider._HeadroomCallback",
        FakeHeadroomCallback,
    )
    # A tuple is not a list; must be converted
    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.litellm.callbacks", ("preexisting_item",)
    )

    AIProvider(Config(enable_headroom=True))

    callbacks = ai_provider.litellm.callbacks
    assert isinstance(callbacks, list)
    assert any(isinstance(c, FakeHeadroomCallback) for c in callbacks)


def test_init_headroom_initializes_missing_callbacks_list(monkeypatch):
    class FakeHeadroomCallback:
        pass

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider._HeadroomCallback",
        FakeHeadroomCallback,
    )
    monkeypatch.setattr("ai_changelog_msg.ai_provider.litellm.callbacks", None)

    AIProvider(Config(enable_headroom=True))

    callbacks = ai_provider.litellm.callbacks
    assert isinstance(callbacks, list)
    assert any(isinstance(c, FakeHeadroomCallback) for c in callbacks)


def test_sanitize_changelog_entry_rejects_mixed_case_system_label():
    """Structured labels must be rejected regardless of case (re.IGNORECASE).

    Kills _sanitize_changelog_entry mutmut_43 (flags=re.IGNORECASE removed) and
    mutmut_45 (regex pattern lowercased), both of which would fail to match
    'System:' or similar mixed-case labels.
    """
    provider = AIProvider.__new__(AIProvider)

    for label in ("System:", "USER:", "Assistant:", "Category:", "Notes:"):
        result = provider._sanitize_changelog_entry(f"{label} This is a prompt leak.")
        assert result is None, f"Expected None for label '{label}', got {result!r}"


def test_sanitize_changelog_entry_joins_lines_with_single_space():
    """Multiple input lines must be joined with a single space, not 'XX XX'.

    Kills _sanitize_changelog_entry mutmut_16:
    ' '.join(lines) changed to 'XX XX'.join(lines).
    """
    provider = AIProvider.__new__(AIProvider)

    content = "First part of\nthe changelog entry."
    result = provider._sanitize_changelog_entry(content)

    assert result is not None
    assert "XX" not in result
    assert "First part of the changelog entry." == result


def test_clean_identity_uses_first_angle_bracket():
    """_clean_identity must split on the FIRST '<', not the last.

    Kills _clean_identity mutmut_4: find('<') changed to rfind('<').
    With rfind, 'Alice <a@b.com> <extra>' would find the second '<'.
    """
    provider = AIProvider.__new__(AIProvider)

    result = provider._clean_identity("Alice Smith <alice@example.com> <secondary>")

    assert result == "Alice Smith"


def test_clean_identity_strips_identity_when_bracket_is_at_index_one():
    provider = AIProvider.__new__(AIProvider)

    result = provider._clean_identity("A<alice@example.com>")

    assert result == "A"


def test_clean_identity_preserves_leading_angle_bracket_identity():
    provider = AIProvider.__new__(AIProvider)

    result = provider._clean_identity("<anonymous@example.com>")

    assert result == "<anonymous@example.com>"


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_sanitize_changelog_entry_returns_none_for_none_input():
    """_sanitize_changelog_entry must return None when content is None."""
    provider = AIProvider.__new__(AIProvider)

    assert provider._sanitize_changelog_entry(None) is None


def test_sanitize_changelog_entry_returns_none_for_blank_lines_only():
    """_sanitize_changelog_entry must return None when all content lines are blank."""
    provider = AIProvider.__new__(AIProvider)

    assert provider._sanitize_changelog_entry("\n\n   \n") is None


def test_sanitize_changelog_entry_returns_none_for_leading_period_sentence():
    """_sanitize_changelog_entry returns None when content triggers the prompt-leak check."""
    provider = AIProvider.__new__(AIProvider)

    # A line matching PROMPT_LEAK_RE should cause return None
    result = provider._sanitize_changelog_entry("Summary: Added new feature.")

    assert result is None


def test_should_pull_missing_ollama_model_returns_false_for_non_ollama_model():
    """_should_pull_missing_ollama_model must return False for non-ollama models."""
    config = Config(model="gpt-4o")
    provider = AIProvider.__new__(AIProvider)
    provider.model = config.model
    provider.config = config

    result = provider._should_pull_missing_ollama_model(RuntimeError("model not found"))

    assert result is False


def test_pull_ollama_model_raises_runtime_error_for_url_error(monkeypatch):
    """_pull_ollama_model must raise RuntimeError when the Ollama API is unreachable."""
    from urllib import error as urllib_error

    import pytest

    def _fail_urlopen(*args, **kwargs):
        raise urllib_error.URLError("connection refused")

    monkeypatch.setattr(
        "ai_changelog_msg.ai_provider.urllib_request.urlopen", _fail_urlopen
    )

    config = Config(model="ollama/llama3.1")
    provider = AIProvider.__new__(AIProvider)
    provider.model = config.model
    provider.config = config

    with pytest.raises(RuntimeError, match="Ollama API is not reachable"):
        provider._pull_ollama_model()
