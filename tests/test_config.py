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

import pytest

from ai_changelog_msg.config import Config


class TestConfig:
    """Test configuration management."""

    def test_config_initialization(self):
        """Test basic config initialization."""
        config = Config(model="gpt-4", namespace="test-notes")
        assert config.model == "gpt-4"
        assert config.namespace == "test-notes"

    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        assert config.model == Config.get_default_model()
        assert config.namespace == "ai-changelog"
        assert config.retry_attempts == 3
        assert config.retry_backoff_seconds == 1.0

    def test_config_from_env(self):
        """Test configuration from environment."""
        config = Config.from_env()
        assert config.model is not None
        assert config.namespace is not None

    def test_config_default_model_for_apple_silicon(self, monkeypatch):
        """Test Apple Silicon default model resolver."""
        monkeypatch.setattr("ai_changelog_msg.config.platform.system", lambda: "Darwin")
        monkeypatch.setattr("ai_changelog_msg.config.platform.machine", lambda: "arm64")

        assert Config.get_default_model() == "ollama/llama3.1:8b-instruct-q4_K_M"

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            Config(model="")

        with pytest.raises(ValueError):
            Config(namespace="")

        with pytest.raises(ValueError):
            Config(max_diff_size=-1)

        with pytest.raises(ValueError):
            Config(max_diff_size=0)

        with pytest.raises(ValueError):
            Config(api_timeout=0)

        with pytest.raises(ValueError):
            Config(retry_attempts=0)

        with pytest.raises(ValueError):
            Config(retry_backoff_seconds=0)

    def test_config_from_env_reads_litellm_headers_json(self, monkeypatch):
        """Test optional LiteLLM header overrides from environment."""
        monkeypatch.setenv(
            "CHANGELOG_LITELLM_HEADERS_JSON",
            '{"X-Org": "platform", "X-Product": "ai-changelog"}',
        )

        config = Config.from_env()

        assert config.litellm_api_base is None
        assert config.litellm_api_key is None
        assert config.litellm_extra_headers == {
            "X-Org": "platform",
            "X-Product": "ai-changelog",
        }

    def test_config_from_env_rejects_invalid_headers_json(self, monkeypatch):
        """Test invalid JSON in LiteLLM headers environment variable."""
        monkeypatch.setenv("CHANGELOG_LITELLM_HEADERS_JSON", "not-json")

        with pytest.raises(ValueError, match="must be valid JSON"):
            Config.from_env()

    def test_config_from_env_parses_headroom_flag(self, monkeypatch):
        """Test optional Headroom toggle from environment."""
        monkeypatch.setenv("CHANGELOG_ENABLE_HEADROOM", "true")

        config = Config.from_env()

        assert config.enable_headroom is True

    def test_config_from_env_rejects_invalid_headroom_flag(self, monkeypatch):
        """Test invalid Headroom toggle value in environment."""
        monkeypatch.setenv("CHANGELOG_ENABLE_HEADROOM", "sometimes")

        with pytest.raises(ValueError, match="CHANGELOG_ENABLE_HEADROOM"):
            Config.from_env()

    def test_config_from_env_enables_headroom_by_default(self, monkeypatch):
        """Test Headroom default is enabled when env var is unset."""
        monkeypatch.delenv("CHANGELOG_ENABLE_HEADROOM", raising=False)

        config = Config.from_env()

        assert config.enable_headroom is True

    def test_config_from_env_allows_explicit_headroom_disable(self, monkeypatch):
        """Test explicit disable value overrides default-enabled behavior."""
        monkeypatch.setenv("CHANGELOG_ENABLE_HEADROOM", "off")

        config = Config.from_env()

        assert config.enable_headroom is False

    def test_config_from_env_reads_retry_settings(self, monkeypatch):
        """Test retry settings loaded from environment."""
        monkeypatch.setenv("CHANGELOG_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("CHANGELOG_RETRY_BACKOFF_SECONDS", "2.5")

        config = Config.from_env()

        assert config.retry_attempts == 5
        assert config.retry_backoff_seconds == 2.5

    def test_config_from_env_rejects_invalid_retry_settings(self, monkeypatch):
        """Test invalid retry setting values from environment."""
        monkeypatch.setenv("CHANGELOG_RETRY_ATTEMPTS", "0")
        with pytest.raises(ValueError, match="CHANGELOG_RETRY_ATTEMPTS"):
            Config.from_env()

        monkeypatch.setenv("CHANGELOG_RETRY_ATTEMPTS", "3")
        monkeypatch.setenv("CHANGELOG_RETRY_BACKOFF_SECONDS", "0")
        with pytest.raises(ValueError, match="CHANGELOG_RETRY_BACKOFF_SECONDS"):
            Config.from_env()

    def test_config_from_env_uses_default_values(self, monkeypatch):
        """Test that from_env uses correct defaults when env vars are absent."""
        monkeypatch.delenv("CHANGELOG_MODEL", raising=False)
        monkeypatch.delenv("CHANGELOG_NAMESPACE", raising=False)
        monkeypatch.delenv("CHANGELOG_RETRY_ATTEMPTS", raising=False)
        monkeypatch.delenv("CHANGELOG_RETRY_BACKOFF_SECONDS", raising=False)

        config = Config.from_env()

        assert config.model == Config.get_default_model()
        assert config.namespace == "ai-changelog"
        assert config.retry_attempts == 3
        assert config.retry_backoff_seconds == 1.0

    def test_config_get_default_model_for_non_apple(self, monkeypatch):
        """Test non-Apple Silicon default model resolver."""
        monkeypatch.setattr("ai_changelog_msg.config.platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "ai_changelog_msg.config.platform.machine", lambda: "x86_64"
        )

        assert Config.get_default_model() == "ollama/llama3.1"
