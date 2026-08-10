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

from ai_changelog_msg.config import Config, _parse_optional_bool


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

    def test_config_boundary_max_diff_size(self):
        """Test boundary conditions for max_diff_size validation."""
        # 1 is valid (positive)
        config = Config(max_diff_size=1)
        assert config.max_diff_size == 1

        # Negative should fail
        with pytest.raises(ValueError, match="Max diff size must be positive"):
            Config(max_diff_size=-1)

    def test_config_boundary_api_timeout(self):
        """Test boundary conditions for api_timeout validation."""
        # 1 is valid (positive)
        config = Config(api_timeout=1)
        assert config.api_timeout == 1

        # Negative should fail
        with pytest.raises(ValueError, match="API timeout must be positive"):
            Config(api_timeout=-1)

    def test_config_boundary_retry_attempts(self):
        """Test boundary conditions for retry_attempts validation."""
        # 1 is valid (positive)
        config = Config(retry_attempts=1)
        assert config.retry_attempts == 1

        # Negative should fail
        with pytest.raises(ValueError, match="Retry attempts must be positive"):
            Config(retry_attempts=-1)

    def test_config_boundary_retry_backoff(self):
        """Test boundary conditions for retry_backoff_seconds validation."""
        # Very small positive value is valid
        config = Config(retry_backoff_seconds=0.1)
        assert config.retry_backoff_seconds == 0.1

        # Negative should fail
        with pytest.raises(ValueError, match="Retry backoff seconds must be positive"):
            Config(retry_backoff_seconds=-0.1)

    def test_config_api_calls_timeout_none_accepted(self):
        """Test that api_calls_timeout can be None."""
        config = Config(api_calls_timeout=None)
        assert config.api_calls_timeout is None

    def test_config_litellm_headers_validation(self):
        """Test LiteLLM extra headers validation."""
        # Valid headers
        config = Config(litellm_extra_headers={"X-Custom": "value"})
        assert config.litellm_extra_headers == {"X-Custom": "value"}

        # Invalid - not a dict
        with pytest.raises(ValueError, match="must be a dictionary"):
            Config(litellm_extra_headers="not-a-dict")

        # Invalid - non-string key
        with pytest.raises(TypeError, match="must contain string keys"):
            Config(litellm_extra_headers={1: "value"})

        # Invalid - non-string value
        with pytest.raises(TypeError, match="must contain string keys and values"):
            Config(litellm_extra_headers={"key": 123})

    def test_parse_optional_bool_uses_default_when_none(self):
        """Test that _parse_optional_bool uses default when raw is None."""
        # When raw is None, the default should be returned
        assert Config._parse_optional_bool(None, "TEST_VAR", default=True) is True
        assert Config._parse_optional_bool(None, "TEST_VAR", default=False) is False

    def test_parse_optional_bool_all_truthy_values(self):
        """Test all accepted truthy values."""
        for truthy in ["1", "true", "yes", "on", "TRUE", "YES", "ON"]:
            assert (
                Config._parse_optional_bool(truthy, "TEST_VAR") is True
            ), f"Failed for {truthy}"

    def test_parse_optional_bool_all_falsy_values(self):
        """Test all accepted falsy values."""
        for falsy in ["0", "false", "no", "off", "", "FALSE", "NO", "OFF"]:
            assert (
                Config._parse_optional_bool(falsy, "TEST_VAR") is False
            ), f"Failed for {falsy}"

    def test_parse_optional_bool_with_whitespace(self):
        """Test boolean parsing with leading/trailing whitespace."""
        assert Config._parse_optional_bool("  true  ", "TEST_VAR") is True
        assert Config._parse_optional_bool("  false  ", "TEST_VAR") is False

    def test_parse_optional_bool_implicit_default_is_false(self):
        """Test that implicit default parameter is False, not True."""
        # When None is passed without explicit default, should return False
        result = Config._parse_optional_bool(None, "TEST_VAR")
        assert result is False

    def test_module_parse_optional_bool_implicit_default_is_false(self):
        """Test module-level helper implicit default remains False."""
        result = _parse_optional_bool(None, "TEST_VAR")
        assert result is False

    def test_parse_positive_int_boundary(self):
        """Test positive integer parsing at boundary."""
        assert Config._parse_positive_int("1", "TEST_VAR", default=0) == 1

    def test_parse_positive_int_uses_default_when_none(self):
        """Test that default is used when raw is None."""
        assert Config._parse_positive_int(None, "TEST_VAR", default=42) == 42

    def test_parse_positive_int_rejects_zero(self):
        """Test that zero is rejected."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            Config._parse_positive_int("0", "TEST_VAR", default=1)

    def test_parse_positive_float_boundary(self):
        """Test positive float parsing at boundary."""
        assert Config._parse_positive_float("0.1", "TEST_VAR", default=0.0) == 0.1

    def test_parse_positive_float_uses_default_when_none(self):
        """Test that default is used when raw is None."""
        assert Config._parse_positive_float(None, "TEST_VAR", default=3.14) == 3.14

    def test_parse_positive_float_rejects_zero(self):
        """Test that zero is rejected."""
        with pytest.raises(ValueError, match="must be a positive number"):
            Config._parse_positive_float("0.0", "TEST_VAR", default=1.0)

    def test_parse_headers_json_roundtrip(self):
        """Test JSON parsing for headers."""
        headers = {"X-Key-1": "value1", "X-Key-2": "value2"}
        import json

        raw = json.dumps(headers)
        result = Config._parse_headers_json(raw)
        assert result == headers

    def test_parse_headers_json_rejects_non_dict(self):
        """Test that JSON arrays are rejected."""
        with pytest.raises(TypeError, match="must be a JSON object"):
            Config._parse_headers_json('["not", "an", "object"]')

    def test_parse_headers_json_requires_string_values(self):
        """Test that non-string header values are rejected."""
        import json

        with pytest.raises(TypeError, match="must be strings"):
            Config._parse_headers_json(json.dumps({"key": 123}))

    def test_config_from_env_reads_model_from_env(self, monkeypatch):
        """Test that from_env specifically reads CHANGELOG_MODEL."""
        monkeypatch.setenv("CHANGELOG_MODEL", "custom-model")
        monkeypatch.delenv("CHANGELOG_NAMESPACE", raising=False)

        config = Config.from_env()

        assert config.model == "custom-model"

    def test_config_from_env_reads_namespace_from_env(self, monkeypatch):
        """Test that from_env specifically reads CHANGELOG_NAMESPACE."""
        monkeypatch.delenv("CHANGELOG_MODEL", raising=False)
        monkeypatch.setenv("CHANGELOG_NAMESPACE", "custom-namespace")

        config = Config.from_env()

        assert config.namespace == "custom-namespace"

    def test_config_from_env_model_override_beats_env(self, monkeypatch):
        """Test that overrides take precedence over environment variables."""
        monkeypatch.setenv("CHANGELOG_MODEL", "env-model")

        config = Config.from_env(model="override-model")

        assert config.model == "override-model"

    def test_config_from_env_namespace_override_beats_env(self, monkeypatch):
        """Test that namespace override beats environment."""
        monkeypatch.setenv("CHANGELOG_NAMESPACE", "env-namespace")

        config = Config.from_env(namespace="override-namespace")

        assert config.namespace == "override-namespace"

    def test_config_from_env_reads_api_base(self, monkeypatch):
        """Test LiteLLM API base URL reading from environment."""
        # API base is read from native LiteLLM env vars, not CHANGELOG_*
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

        config = Config.from_env()

        # When not set, should be None
        assert config.litellm_api_base is None

    def test_config_from_env_reads_retry_attempts_from_env(self, monkeypatch):
        """Test that CHANGELOG_RETRY_ATTEMPTS is read."""
        monkeypatch.setenv("CHANGELOG_RETRY_ATTEMPTS", "7")
        monkeypatch.delenv("CHANGELOG_RETRY_BACKOFF_SECONDS", raising=False)
        monkeypatch.delenv("CHANGELOG_ENABLE_HEADROOM", raising=False)

        config = Config.from_env()

        assert config.retry_attempts == 7

    def test_config_from_env_reads_retry_backoff_from_env(self, monkeypatch):
        """Test that CHANGELOG_RETRY_BACKOFF_SECONDS is read."""
        monkeypatch.setenv("CHANGELOG_RETRY_BACKOFF_SECONDS", "4.5")
        monkeypatch.delenv("CHANGELOG_RETRY_ATTEMPTS", raising=False)
        monkeypatch.delenv("CHANGELOG_ENABLE_HEADROOM", raising=False)

        config = Config.from_env()

        assert config.retry_backoff_seconds == 4.5

    def test_config_get_model_returns_model_field(self):
        """Test that get_model() returns the model field."""
        config = Config(model="test-model")
        assert config.get_model() == "test-model"

    def test_config_get_namespace_returns_namespace_field(self):
        """Test that get_namespace() returns the namespace field."""
        config = Config(namespace="test-namespace")
        assert config.get_namespace() == "test-namespace"

    def test_config_model_auto_resolves_at_init(self):
        """Test that 'auto' model value is resolved to platform-specific default."""
        config = Config(model="auto")
        # Should be resolved to the default model, not "auto"
        assert config.model != "auto"
        assert config.model == Config.get_default_model()

    def test_config_from_env_resolves_auto_model(self, monkeypatch):
        """Test that from_env resolves 'auto' model."""
        monkeypatch.delenv("CHANGELOG_MODEL", raising=False)

        config = Config.from_env()

        # Should be resolved to default, not "auto"
        assert config.model != "auto"
        assert config.model == Config.get_default_model()


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_parse_positive_int_raises_for_non_integer_string():
    """_parse_positive_int must raise ValueError when raw is not a valid integer."""
    import pytest

    with pytest.raises(ValueError, match="must be a positive integer"):
        Config._parse_positive_int("not-an-int", "TEST_VAR", default=1)


def test_parse_positive_float_raises_for_non_float_string():
    """_parse_positive_float must raise ValueError when raw is not a valid number."""
    import pytest

    with pytest.raises(ValueError, match="must be a positive number"):
        Config._parse_positive_float("not-a-float", "TEST_VAR", default=1.0)
