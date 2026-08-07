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

"""AI provider abstraction for generating commit summaries via LiteLLM."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from json import JSONDecodeError
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

import litellm

try:
    from headroom.integrations.litellm_callback import (
        HeadroomCallback as _HeadroomCallback,
    )
except ImportError:  # pragma: no cover - optional dependency
    _HeadroomCallback = None

from ai_changelog_msg.config import Config

logger = logging.getLogger(__name__)

PR_AUTHOR_RE = re.compile(
    r"^Merge pull request\s+#\d+\s+from\s+(?P<author>[A-Za-z0-9_.-]+?)/",
    re.IGNORECASE,
)
APPROVER_RE = re.compile(
    r"^\s*(?:Approved-by|Reviewed-by|Acked-by)\s*:\s*(?P<identity>.+?)\s*$",
    re.IGNORECASE,
)
PROMPT_LEAK_RE = re.compile(
    r"(?:"
    r"###\s*(?:System|User|Assistant|Output|Solution|Summary|Explanation|Notes?)\b"
    r"|Rewrite\s+the\s+summary\s+above"
    r"|Category\s*:\s*(?:Added|Changed|Fixed|Removed)"
    r"|Original\s+Commit\s+Message"
    r"|Existing\s+Summary"
    r"|Keep\s+a\s+Changelog\s+entry\s+sentence"
    r"|```"
    r")",
    re.IGNORECASE,
)
LEADING_LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
LEADING_QUOTE_RE = re.compile(r'^["\']+|["\']+$')
OLLAMA_MODEL_NOT_FOUND_RE = re.compile(
    r"(?:model\s+['\"]?.+?['\"]?\s+not\s+found|pull\s+the\s+model\s+first)",
    re.IGNORECASE,
)
RETRYABLE_LLM_ERROR_RE = re.compile(
    r"(?:"
    r"timeout"
    r"|timed\s+out"
    r"|apiconnectionerror"
    r"|connection\s+error"
    r"|connection\s+refused"
    r"|temporarily\s+unavailable"
    r"|service\s+unavailable"
    r"|rate\s+limit"
    r"|too\s+many\s+requests"
    r"|\b429\b"
    r"|\b500\b"
    r"|\b502\b"
    r"|\b503\b"
    r"|\b504\b"
    r")",
    re.IGNORECASE,
)


class AIProvider:
    """LiteLLM-backed provider that summarises git commit diffs.

    Wraps :func:`litellm.completion` so that any model supported by LiteLLM
    (Ollama, OpenAI, Anthropic, etc.) can be used without changing application
    code. Provides two AI tasks:

    - commit-level note generation from diffs (:meth:`summarize_diff`)
    - changelog sentence normalization (:meth:`generate_changelog_entry`)

    Initialization also suppresses verbose LiteLLM diagnostic output so CLI
    progress and application logs remain readable.

    Args:
        config: Runtime configuration supplying the model identifier,
            timeout, and diff-size limit.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.model = config.get_model()
        self._litellm_kwargs: dict[str, object] = {}
        if config.litellm_api_base:
            self._litellm_kwargs["api_base"] = config.litellm_api_base
        if config.litellm_api_key:
            self._litellm_kwargs["api_key"] = config.litellm_api_key
        if config.litellm_extra_headers:
            self._litellm_kwargs["extra_headers"] = config.litellm_extra_headers
        # Keep LiteLLM quiet so progress/log output stays readable.
        os.environ["LITELLM_LOG"] = "ERROR"
        # Keep LiteLLM's noisy diagnostic/info output disabled by default so
        # application logs remain readable.
        if hasattr(litellm, "set_verbose"):
            litellm.set_verbose = False
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)
        logging.getLogger("litellm").setLevel(logging.WARNING)
        self._enable_headroom_compression_if_requested()
        # Keep retries in application code so this tool does not depend on
        # optional LiteLLM tenacity extras at runtime.
        litellm.num_retries = 0
        litellm.timeout = config.api_timeout
        self._max_completion_attempts = config.retry_attempts
        self._base_retry_delay_seconds = config.retry_backoff_seconds
        logger.debug(
            "AIProvider initialised: model=%s timeout=%s retries=%s backoff=%.2fs",
            self.model,
            config.api_timeout,
            self._max_completion_attempts,
            self._base_retry_delay_seconds,
        )

    def _enable_headroom_compression_if_requested(self) -> None:
        """Enable Headroom token compression for LiteLLM requests.

        When ``Config.enable_headroom`` is true, this method registers
        :class:`headroom.integrations.litellm_callback.HeadroomCallback`
        exactly once in ``litellm.callbacks``.

        Raises:
            RuntimeError: If Headroom was requested but is not installed.
        """
        if not self.config.enable_headroom:
            return

        if _HeadroomCallback is None:
            raise RuntimeError(
                "Headroom is enabled but not installed. Install with: "
                "pip install headroom-ai"
            )

        callbacks: Any = getattr(litellm, "callbacks", None)
        if callbacks is None:
            callbacks = []
            litellm.callbacks = callbacks

        if not isinstance(callbacks, list):
            callbacks = list(callbacks)
            litellm.callbacks = callbacks

        if any(isinstance(callback, _HeadroomCallback) for callback in callbacks):
            return

        callbacks.append(_HeadroomCallback())
        logger.info("Headroom compression enabled for LiteLLM requests")

    def _completion_with_ollama_auto_pull(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Any:
        """Call LiteLLM and auto-pull missing Ollama models when needed."""
        try:
            return litellm.completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **self._litellm_kwargs,
            )
        except Exception as error:
            if not self._should_pull_missing_ollama_model(error):
                raise

            self._pull_ollama_model()
            return litellm.completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **self._litellm_kwargs,
            )

    def _is_retryable_completion_error(self, error: Exception) -> bool:
        """Return ``True`` when *error* should trigger a retry."""
        return bool(RETRYABLE_LLM_ERROR_RE.search(str(error)))

    def _completion_with_retry(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Any:
        """Call the model with bounded retries for transient failures."""
        for attempt in range(1, self._max_completion_attempts + 1):
            try:
                return self._completion_with_ollama_auto_pull(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as error:
                if (
                    not self._is_retryable_completion_error(error)
                    or attempt >= self._max_completion_attempts
                ):
                    raise

                delay_seconds = self._base_retry_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Transient AI API error on attempt %d/%d: %s. Retrying in %.1fs",
                    attempt,
                    self._max_completion_attempts,
                    error,
                    delay_seconds,
                )
                time.sleep(delay_seconds)

        raise RuntimeError("Unreachable retry state while calling AI provider")

    def _should_pull_missing_ollama_model(self, error: Exception) -> bool:
        """Return ``True`` when *error* indicates a missing Ollama model."""
        if not self.model.startswith("ollama/"):
            return False
        return bool(OLLAMA_MODEL_NOT_FOUND_RE.search(str(error)))

    def _pull_ollama_model(self) -> None:
        """Pull the configured Ollama model through the Ollama HTTP API.

        Raises:
            RuntimeError: If pulling fails or the Ollama API is unavailable.
        """
        model_name = self.model.removeprefix("ollama/")
        logger.info("Ollama model '%s' not available locally; pulling", model_name)

        api_base = self.config.litellm_api_base or "http://localhost:11434"
        parsed_base = urllib_parse.urlsplit(api_base)
        if parsed_base.scheme and parsed_base.netloc:
            pull_base = f"{parsed_base.scheme}://{parsed_base.netloc}"
        else:
            pull_base = "http://localhost:11434"

        payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
        request = urllib_request.Request(
            f"{pull_base}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(
                request,
                timeout=self.config.api_timeout,
            ) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib_error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace").strip() or str(
                error
            )
            raise RuntimeError(
                f"Failed to pull Ollama model '{model_name}': {details}"
            ) from error
        except (urllib_error.URLError, OSError) as error:
            raise RuntimeError(
                "Ollama API is not reachable; ensure Ollama is running and accessible"
            ) from error

        if body.strip():
            try:
                payload_data = json.loads(body)
                if isinstance(payload_data, dict) and payload_data.get("error"):
                    raise RuntimeError(
                        f"Failed to pull Ollama model '{model_name}': "
                        f"{payload_data['error']}"
                    )
            except (JSONDecodeError, AttributeError):
                # Some Ollama versions stream line-delimited JSON; if parsing
                # fails, we still accept a successful HTTP response.
                pass

    def summarize_diff(
        self,
        commit_message: str,
        diff: str,
        author: str | None = None,
    ) -> str:
        """Generate an AI summary for a single git commit diff.

        The diff is truncated to :attr:`~Config.max_diff_size` characters
        before being forwarded to the model, keeping large commits within
        typical context-window limits.

        Args:
            commit_message: Original commit message written by the author.
            diff: Raw unified diff text for the commit.
            author: Display name of the commit author.  When provided it is
                prepended to the prompt for additional context.

        Returns:
            A plain-text summary produced by the model, or a sentinel string
            when the diff is empty or the model returns no content.

        Raises:
            RuntimeError: When the underlying AI API call fails.

        Examples:
            An empty (or whitespace-only) diff is short-circuited without
            making any API call:

            >>> provider = AIProvider.__new__(AIProvider)
            >>> provider.summarize_diff("fix: typo", "")
            '[No changes to summarize]'
            >>> provider.summarize_diff("fix: typo", "   ")
            '[No changes to summarize]'
        """
        if not diff.strip():
            return "[No changes to summarize]"

        max_chars = self.config.max_diff_size
        if len(diff) > max_chars:
            remaining_chars = len(diff) - max_chars
            logger.debug("Truncating diff from %d to %d chars", len(diff), max_chars)
            diff = (
                diff[:max_chars]
                + f"\n... (truncated, {remaining_chars} more characters)"
            )

        prompt = self._build_prompt(commit_message, diff, author)
        logger.debug(
            "Sending request to model '%s' (prompt length: %d chars)",
            self.model,
            len(prompt),
        )

        try:
            response = self._completion_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You write concise git-note summaries for a Keep a Changelog style "
                            "workflow. First identify the core thesis of the change and only the most "
                            "important supporting impacts. Ignore minor refactors, repetitive examples, "
                            "and low-level implementation trivia. Keep the summary objective and grounded "
                            "in the commit content; do not add personal opinions or outside analysis. "
                            "Output plain text only with exactly one paragraph of 2 to 4 sentences and "
                            "typically at most 80 words. Never drop critical information to satisfy length. "
                            "Preserve this priority order when condensing: (1) breaking behavior or migration "
                            "requirements, (2) API or CLI contract changes, (3) security impact, (4) config "
                            "schema changes, (5) primary user or maintainer outcome. The first sentence "
                            "must state what changed and why it "
                            "matters to users or maintainers. Use your own words and avoid direct "
                            "copying from the commit message or diff. Do not include headings, lead-ins, "
                            "labels, markdown, bullets, numbered lists, code fences, or quote marks. "
                            "Never write phrases such as 'Here is a summary of the changes' or "
                            "'Optional additional context'. Always mention breaking behavior, API or CLI "
                            "changes, config schema changes, migration steps, and security impact when "
                            "present. Never mention file paths, variable names, line numbers, commit "
                            "hashes, or reviewer metadata."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            logger.debug("Response received from model '%s'", self.model)
        except Exception as error:
            logger.error("API call to '%s' failed: %s", self.model, error)
            raise RuntimeError(f"AI API call failed: {error}") from error

        summary = response.choices[0].message.content
        return summary.strip() if summary else "[Failed to generate summary]"

    def generate_changelog_entry(
        self,
        commit_message: str,
        note: str,
        category: str,
        is_breaking: bool = False,
    ) -> str:
        """Generate a changelog-ready single-sentence entry from a git note.

        Args:
            commit_message: Original commit subject or full message.
            note: Existing git note summary for the commit.
            category: Keep a Changelog category inferred for the commit.
            is_breaking: Whether the commit introduces a breaking change.

        Returns:
            A single changelog-ready sentence, or the original *note* if the
            AI call fails or returns no content.
        """
        fallback_entry = note.strip() or commit_message.strip()
        prompt = (
            f"Category: {category}\n"
            f"Breaking Change: {'yes' if is_breaking else 'no'}\n"
            f"Original Commit Message:\n{commit_message}\n\n"
            f"Existing Summary:\n{note}\n\n"
            "Rewrite the summary above into exactly one Keep a Changelog entry sentence. "
            "The sentence must describe the user- or maintainer-visible outcome, not internal "
            "implementation steps. Use the active voice, match the tone to the provided "
            "category intent, and begin with a strong action verb instead of repeating the "
            "category label word. If the change is purely internal with no observable effect, "
            "state that clearly in one sentence. Prefer precise high-impact verbs such as "
            "enabled, introduced, optimized, modernized, hardened, resolved, "
            "stabilized, or simplified when they fit. "
            "Avoid repeating the same opening verb as nearby entries when a natural alternative exists. "
            "Do not start with Added, Changed, Deprecated, Removed, Fixed, or Security. "
            "Do not use markdown, bullets, commit hashes, file paths, "
            "or code identifiers."
        )

        try:
            response = self._completion_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You normalize engineering summaries into one uniform Keep a Changelog "
                            "entry sentence written for a technical audience. Output exactly one "
                            "sentence in plain text with no markdown, list markers, labels, or quotes. "
                            "Start with a strong action verb that matches the provided category intent, "
                            "but do not start with literal labels Added, Changed, Deprecated, Removed, "
                            "Fixed, or Security. Prefer specific high-impact verbs such as "
                            "enabled, introduced, optimized, modernized, hardened, resolved, "
                            "stabilized, or simplified when accurate. Avoid repeating the same opening "
                            "verb in nearby entries when a natural alternative exists. Describe the observable impact "
                            "for developers or operators; "
                            "never describe internal code mechanics. State breaking behavior, API "
                            "contract changes, or migration requirements explicitly. Do not include "
                            "commit hashes, file paths, code identifiers, or implementation trivia. "
                            "Every entry must read as if written by the same author."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.35,
                max_tokens=120,
            )
        except Exception as error:  # noqa: BLE001
            logger.warning("Falling back to note text for changelog entry: %s", error)
            return fallback_entry

        content = response.choices[0].message.content if response.choices else None
        sanitized_content = self._sanitize_changelog_entry(content)
        if sanitized_content is None:
            logger.warning(
                "Discarding invalid changelog entry from model; falling back to note text"
            )
            return fallback_entry
        return sanitized_content

    def _sanitize_changelog_entry(self, content: str | None) -> str | None:
        """Normalize a model-generated changelog sentence.

        Args:
            content: Raw model output for changelog entry generation.

        Returns:
            A single clean sentence when the output is valid, otherwise
            ``None`` so callers can use a deterministic fallback.
        """
        if content is None:
            return None

        lines: list[str] = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = LEADING_LIST_MARKER_RE.sub("", line)
            lines.append(line)

        if not lines:
            return None

        merged = " ".join(lines)
        merged = LEADING_QUOTE_RE.sub("", merged).strip()
        if not merged or PROMPT_LEAK_RE.search(merged):
            return None

        sentence = re.split(r"(?<=[.!?])\s+", merged, maxsplit=1)[0].strip()
        if not sentence:
            return None

        # Reject structured labels that indicate prompt leakage instead of a summary.
        if re.match(
            r"^(?:System|User|Assistant|Output|Solution|Summary|Explanation|Notes?|Category)\s*:",
            sentence,
            flags=re.IGNORECASE,
        ):
            return None

        return sentence

    def _build_prompt(
        self,
        commit_message: str,
        diff: str,
        author: str | None,
    ) -> str:
        """Assemble the user-facing prompt sent to the AI model.

        The prompt is composed of optional identity lines (commit author and,
        when discoverable from commit metadata, PR author and approver), the
        original commit message, the diff fenced in a code block, and a fixed
        instruction sentence.

        Args:
            commit_message: Commit message text.
            diff: Unified diff string (may already be truncated by the
                caller).
            author: Commit author display name, or ``None`` to omit.

        Returns:
            A single string ready to be used as the ``user`` message.

        Examples:
            Without an author the prompt starts with the commit message:

            >>> provider = AIProvider.__new__(AIProvider)
            >>> diff_text = "-foo\\n+bar"
            >>> result = provider._build_prompt("fix: typo", diff_text, None)
            >>> result.startswith("Original Commit Message:")
            True

            With an author the first line is the ``Author:`` header:

            >>> result = provider._build_prompt("fix: typo", diff_text, "Alice")
            >>> result.startswith("Author: Alice")
            True
        """
        pr_author, approver = self._extract_review_metadata(commit_message)
        prompt_parts = []
        if author:
            prompt_parts.append(f"Author: {author}\n")
        if pr_author:
            prompt_parts.append(f"PR Author: {pr_author}\n")
        if approver:
            prompt_parts.append(f"Approver: {approver}\n")
        prompt_parts.append(f"Original Commit Message:\n{commit_message}\n")
        prompt_parts.append(f"Diff:\n```\n{diff}\n```\n")
        prompt_parts.append(
            "Summarization checklist: "
            "(1) Identify the core thesis of the change. "
            "(2) Keep only major supporting points and ignore minor edits. "
            "(3) Write in your own words with an objective tone. "
            "(4) Preserve critical details first: breaking or migration requirements, API or CLI "
            "changes, security impact, config schema changes, then the primary user outcome. "
            "(5) Output exactly one paragraph of 2 to 4 sentences and target 80 words unless "
            "critical details require slightly more. "
            "(6) Start with what changed and why it matters. "
            "(7) Do not output headers or lead-ins such as 'Here is a summary' or "
            "'Optional additional context'."
        )
        return "\n".join(prompt_parts)

    def _extract_review_metadata(
        self, commit_message: str
    ) -> tuple[str | None, str | None]:
        """Extract PR author and approver identities from a commit message.

        This helper supports common merge-commit and trailer formats produced by
        GitHub and related review workflows.

        Args:
            commit_message: Full commit message text.

        Returns:
            A tuple of ``(pr_author, approver)`` where each value may be
            ``None`` when not present.
        """
        pr_author: str | None = None
        approvers: list[str] = []

        for line in commit_message.splitlines():
            if pr_author is None:
                pr_match = PR_AUTHOR_RE.match(line.strip())
                if pr_match:
                    candidate = pr_match.group("author").strip()
                    pr_author = candidate or None

            approver_match = APPROVER_RE.match(line)
            if not approver_match:
                continue
            identity = self._clean_identity(approver_match.group("identity"))
            if identity and identity not in approvers:
                approvers.append(identity)

        approver = ", ".join(approvers) if approvers else None
        return pr_author, approver

    def _clean_identity(self, identity: str) -> str:
        """Normalize identity values captured from commit trailers."""
        value = identity.strip()
        angle_index = value.find("<")
        if angle_index > 0:
            value = value[:angle_index].strip()
        return value
