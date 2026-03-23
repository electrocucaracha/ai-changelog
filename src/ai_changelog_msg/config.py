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

"""Configuration management for AI Changelog Generator."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Runtime configuration for the AI Changelog Message Generator.

    All fields are validated immediately after construction via
    :meth:`__post_init__`.  The recommended way to create an instance from
    the shell environment is :meth:`from_env`.

    Attributes:
        model: LiteLLM model identifier passed to :func:`litellm.completion`.
        namespace: git-notes ``--ref`` namespace used to store summaries.
        api_timeout: Per-request HTTP timeout in seconds.
        max_diff_size: Maximum number of characters of a diff forwarded to
            the model.  Longer diffs are truncated before the API call.
        api_calls_timeout: Optional overall wall-clock timeout in seconds
            for a complete processing run.  ``None`` means no limit.

    Examples:
        Default values are sensible out of the box:

        >>> c = Config()
        >>> c.model
        'ollama/llama3.1'
        >>> c.namespace
        'ai-changelog'

        An empty model string is rejected immediately:

        >>> Config(model="")
        Traceback (most recent call last):
            ...
        ValueError: Model name cannot be empty

        A non-positive diff size is rejected:

        >>> Config(max_diff_size=0)
        Traceback (most recent call last):
            ...
        ValueError: Max diff size must be positive
    """

    model: str = "ollama/llama3.1"
    namespace: str = "ai-changelog"
    api_timeout: int = 60
    max_diff_size: int = 50000
    api_calls_timeout: Optional[int] = 300

    def __post_init__(self) -> None:
        """Validate field values after dataclass initialisation.

        Raises:
            ValueError: When any field contains an invalid value.
        """
        if not self.model:
            raise ValueError("Model name cannot be empty")
        if not self.namespace:
            raise ValueError("Namespace cannot be empty")
        if self.max_diff_size <= 0:
            raise ValueError("Max diff size must be positive")
        if self.api_timeout <= 0:
            raise ValueError("API timeout must be positive")

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """Create a :class:`Config` from environment variables.

        Reads ``CHANGELOG_MODEL`` and ``CHANGELOG_NAMESPACE`` from the
        environment, falling back to built-in defaults when the variables are
        absent.  Any keyword argument in *overrides* takes precedence over
        both the environment and the defaults.

        Args:
            **overrides: Field overrides.  Only ``model`` and ``namespace``
                are recognised; unknown keys are silently ignored.

        Returns:
            A new :class:`Config` instance.

        Examples:
            An override always wins over the environment variable:

            >>> Config.from_env(model="gpt-4o").model
            'gpt-4o'

            Without overrides the default is used when the env var is unset:

            >>> import os
            >>> os.environ.pop("CHANGELOG_MODEL", None)  # ensure unset
            >>> Config.from_env().model
            'ollama/llama3.1'
        """
        model = os.getenv("CHANGELOG_MODEL", "ollama/llama3.1")
        namespace = os.getenv("CHANGELOG_NAMESPACE", "ai-changelog")
        return cls(
            model=overrides.get("model", model),
            namespace=overrides.get("namespace", namespace),
        )

    def get_model(self) -> str:
        """Return the configured LiteLLM model identifier.

        Examples:
            >>> Config(model="ollama/llama3.1").get_model()
            'ollama/llama3.1'
        """
        return self.model

    def get_namespace(self) -> str:
        """Return the git-notes namespace used to store summaries.

        Examples:
            >>> Config(namespace="my-notes").get_namespace()
            'my-notes'
        """
        return self.namespace
