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
        assert config.model == "ollama/llama3.1"
        assert config.namespace == "ai-changelog"

    def test_config_from_env(self):
        """Test configuration from environment."""
        config = Config.from_env()
        assert config.model is not None
        assert config.namespace is not None

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            Config(model="")

        with pytest.raises(ValueError):
            Config(max_diff_size=-1)
