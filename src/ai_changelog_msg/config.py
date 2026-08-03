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

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


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
    api_calls_timeout: int | None = 300
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None
    litellm_extra_headers: dict[str, str] | None = None

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
        if self.litellm_extra_headers is not None:
            if not isinstance(self.litellm_extra_headers, dict):
                raise ValueError("LiteLLM extra headers must be a dictionary")
            for key, value in self.litellm_extra_headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise TypeError(
                        "LiteLLM extra headers must contain string keys and values"
                    )

    @classmethod
    def from_env(cls, **overrides) -> Config:
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
        litellm_api_base = os.getenv("CHANGELOG_LITELLM_API_BASE")
        litellm_api_key = os.getenv("CHANGELOG_LITELLM_API_KEY")
        litellm_extra_headers: dict[str, str] | None = None

        headers_env = os.getenv("CHANGELOG_LITELLM_HEADERS_JSON")
        if headers_env:
            litellm_extra_headers = cls._parse_headers_json(headers_env)

        return cls(
            model=overrides.get("model", model),
            namespace=overrides.get("namespace", namespace),
            litellm_api_base=overrides.get("litellm_api_base", litellm_api_base),
            litellm_api_key=overrides.get("litellm_api_key", litellm_api_key),
            litellm_extra_headers=overrides.get(
                "litellm_extra_headers", litellm_extra_headers
            ),
        )

    @staticmethod
    def _parse_headers_json(raw: str) -> dict[str, str]:
        """Parse a JSON object into string-based HTTP headers."""
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                "CHANGELOG_LITELLM_HEADERS_JSON must be valid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise TypeError("CHANGELOG_LITELLM_HEADERS_JSON must be a JSON object")

        headers: dict[str, str] = {}
        for key, value in parsed.items():
            if not isinstance(key, str):
                raise TypeError("CHANGELOG_LITELLM_HEADERS_JSON keys must be strings")
            if not isinstance(value, str):
                raise TypeError("CHANGELOG_LITELLM_HEADERS_JSON values must be strings")
            headers[key] = value
        return headers

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
