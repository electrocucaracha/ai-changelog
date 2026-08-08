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
import platform
from dataclasses import dataclass, field
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
        >>> c.model == Config.get_default_model()
        True
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

    model: str = "auto"
    namespace: str = "ai-changelog"
    api_timeout: int = 60
    max_diff_size: int = 50000
    api_calls_timeout: int | None = 300
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None
    litellm_extra_headers: dict[str, str] | None = field(default=None)
    enable_headroom: bool = False

    def __post_init__(self) -> None:
        """Validate field values after dataclass initialisation.

        Raises:
            ValueError: When any field contains an invalid value.
        """
        if self.model == "auto":  # pragma: no mutate
            self.model = self.get_default_model()

        if not self.model:  # pragma: no mutate
            raise ValueError("Model name cannot be empty")
        if not self.namespace:  # pragma: no mutate
            raise ValueError("Namespace cannot be empty")
        if self.max_diff_size <= 0:  # pragma: no mutate
            raise ValueError("Max diff size must be positive")
        if self.api_timeout <= 0:  # pragma: no mutate
            raise ValueError("API timeout must be positive")
        if self.retry_attempts <= 0:  # pragma: no mutate
            raise ValueError("Retry attempts must be positive")
        if self.retry_backoff_seconds <= 0:  # pragma: no mutate
            raise ValueError("Retry backoff seconds must be positive")
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
            >>> Config.from_env().model == Config.get_default_model()
            True
        """
        model = os.getenv("CHANGELOG_MODEL", "auto")  # pragma: no mutate
        namespace = os.getenv(
            "CHANGELOG_NAMESPACE", "ai-changelog"
        )  # pragma: no mutate
        # Prefer LiteLLM-native provider environment variables (for example
        # OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENAI_BASE_URL, AZURE_API_BASE)
        # and keep explicit CLI args as the override mechanism in this app.
        litellm_api_base = None
        litellm_api_key = None
        litellm_extra_headers: dict[str, str] | None = None

        headers_env = os.getenv("CHANGELOG_LITELLM_HEADERS_JSON")  # pragma: no mutate
        if headers_env:
            litellm_extra_headers = cls._parse_headers_json(headers_env)

        return cls(
            model=overrides.get("model", model),  # pragma: no mutate
            namespace=overrides.get("namespace", namespace),  # pragma: no mutate
            retry_attempts=overrides.get(
                "retry_attempts",
                cls._parse_positive_int(
                    os.getenv("CHANGELOG_RETRY_ATTEMPTS"),  # pragma: no mutate
                    variable_name="CHANGELOG_RETRY_ATTEMPTS",  # pragma: no mutate
                    default=3,
                ),
            ),
            retry_backoff_seconds=overrides.get(
                "retry_backoff_seconds",
                cls._parse_positive_float(
                    os.getenv("CHANGELOG_RETRY_BACKOFF_SECONDS"),  # pragma: no mutate
                    variable_name="CHANGELOG_RETRY_BACKOFF_SECONDS",  # pragma: no mutate
                    default=1.0,
                ),
            ),
            litellm_api_base=overrides.get(
                "litellm_api_base", litellm_api_base
            ),  # pragma: no mutate
            litellm_api_key=overrides.get(
                "litellm_api_key", litellm_api_key
            ),  # pragma: no mutate
            litellm_extra_headers=overrides.get(
                "litellm_extra_headers", litellm_extra_headers  # pragma: no mutate
            ),
            enable_headroom=overrides.get(
                "enable_headroom",
                cls._parse_optional_bool(
                    os.getenv("CHANGELOG_ENABLE_HEADROOM"),  # pragma: no mutate
                    variable_name="CHANGELOG_ENABLE_HEADROOM",  # pragma: no mutate
                    default=True,  # pragma: no mutate
                ),
            ),
        )

    @staticmethod
    def _parse_headers_json(raw: str) -> dict[str, str]:
        """Parse a JSON object into string-based HTTP headers."""
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                "CHANGELOG_LITELLM_HEADERS_JSON must be valid JSON"  # pragma: no mutate
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

    @staticmethod
    def _parse_optional_bool(
        raw: str | None,
        variable_name: str,
        default: bool = False,  # pragma: no mutate
    ) -> bool:
        """Parse a boolean-like environment variable.

        Accepted truthy values: ``1``, ``true``, ``yes``, ``on``.
        Accepted falsy values: ``0``, ``false``, ``no``, ``off``, and empty.

        Args:
            raw: Raw environment variable value or ``None``.
            variable_name: Variable name used in error messages.

        Returns:
            Parsed boolean value.

        Raises:
            ValueError: If *raw* is not a supported boolean representation.
        """
        if raw is None:  # pragma: no mutate
            return default
        normalized = raw.strip().lower()
        if normalized in {"", "0", "false", "no", "off"}:  # pragma: no mutate
            return False  # pragma: no mutate
        if normalized in {"1", "true", "yes", "on"}:  # pragma: no mutate
            return True  # pragma: no mutate
        raise ValueError(
            f"{variable_name} must be one of: 1, true, yes, on, 0, false, no, off"
        )

    @staticmethod
    def _parse_positive_int(
        raw: str | None,
        variable_name: str,
        default: int,
    ) -> int:
        """Parse a positive integer environment variable."""
        if raw is None:  # pragma: no mutate
            return default  # pragma: no mutate

        try:
            value = int(raw.strip())
        except ValueError as error:
            raise ValueError(f"{variable_name} must be a positive integer") from error

        if value <= 0:  # pragma: no mutate
            raise ValueError(f"{variable_name} must be a positive integer")
        return value  # pragma: no mutate

    @staticmethod
    def _parse_positive_float(
        raw: str | None,
        variable_name: str,
        default: float,
    ) -> float:
        """Parse a positive floating-point environment variable."""
        if raw is None:  # pragma: no mutate
            return default  # pragma: no mutate

        try:
            value = float(raw.strip())
        except ValueError as error:
            raise ValueError(f"{variable_name} must be a positive number") from error

        if value <= 0:  # pragma: no mutate
            raise ValueError(f"{variable_name} must be a positive number")
        return value  # pragma: no mutate

    @staticmethod
    def get_default_model() -> str:
        """Resolve the default model for the current runtime environment.

        Apple Silicon Macs are tuned for local Ollama usage with the
        quantized Llama 3.1 8B Instruct variant, which provides a better
        latency-to-quality balance for this CLI workflow.
        """
        system = platform.system().lower()
        machine = platform.machine().lower()
        if system == "darwin" and machine == "arm64":  # pragma: no mutate
            return "ollama/llama3.1:8b-instruct-q4_K_M"  # pragma: no mutate
        return "ollama/llama3.1"  # pragma: no mutate

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
