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
import os
from typing import Optional

import litellm

from ai_changelog_msg.config import Config

logger = logging.getLogger(__name__)


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
        litellm.num_retries = 3
        litellm.timeout = config.api_timeout
        logger.debug(
            "AIProvider initialised: model=%s timeout=%s",
            self.model,
            config.api_timeout,
        )

    def summarize_diff(
        self,
        commit_message: str,
        diff: str,
        author: Optional[str] = None,
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
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You produce standardized release-note summaries for git commits. "
                            "These summaries are stored as git notes and later parsed into a "
                            "Keep a Changelog style CHANGELOG.md. Follow this output contract "
                            "exactly. Output plain text only. Do not use markdown, headings, "
                            "bullets, numbered lists, labels like Summary or Why, code fences, "
                            "or emphasis markers. Return either one or two short paragraphs. "
                            "Paragraph 1 is mandatory and must be exactly one sentence that starts "
                            "with an action verb (Added, Fixed, Changed, Removed, Improved, or "
                            "Refactored), clearly states the primary outcome, and ends with a period. "
                            "Paragraph 2 is optional and must be 1-2 sentences describing scope, "
                            "motivation, and impact only when useful for maintainers or users. "
                            "Explicitly mention breaking changes, behavioral changes, API or CLI "
                            "changes, config changes, migration implications, or security impact when "
                            "present. Avoid line-by-line implementation details, commit metadata, file "
                            "paths, and vague filler language. Keep the style neutral, concise, and "
                            "consistent across commits."
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
        prompt = (
            f"Category: {category}\n"
            f"Breaking Change: {'yes' if is_breaking else 'no'}\n"
            f"Original Commit Message:\n{commit_message}\n\n"
            f"Existing Summary:\n{note}\n\n"
            "Rewrite this into exactly one changelog-ready sentence. "
            "Keep it factual and concise. Focus on the user- or maintainer-visible outcome. "
            "Do not use markdown, bullets, commit hashes, file names, or implementation trivia. "
            "If the change is internal-only, say that clearly."
        )

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You rewrite engineering summaries into one standardized changelog "
                            "sentence. Output exactly one sentence in plain text with no markdown, "
                            "no list markers, no labels, and no quotes. Start with a suitable action "
                            "verb that aligns with the provided category. Keep it factual, specific, "
                            "and user- or maintainer-facing. Mention breaking behavior explicitly when "
                            "applicable. Do not include commit hashes, file paths, code identifiers, "
                            "or implementation trivia."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=120,
            )
        except Exception as error:
            logger.warning("Falling back to note text for changelog entry: %s", error)
            return note.strip() or commit_message.strip()

        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else (note.strip() or commit_message.strip())

    def _build_prompt(
        self,
        commit_message: str,
        diff: str,
        author: Optional[str],
    ) -> str:
        """Assemble the user-facing prompt sent to the AI model.

        The prompt is composed of an optional author line, the original
        commit message, the diff fenced in a code block, and a fixed
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
        prompt_parts = []
        if author:
            prompt_parts.append(f"Author: {author}\n")
        prompt_parts.append(f"Original Commit Message:\n{commit_message}\n")
        prompt_parts.append(f"Diff:\n```\n{diff}\n```\n")
        prompt_parts.append(
            "Please provide a clear, concise summary of the changes made in this commit. "
            "Focus on the 'what' and 'why' rather than detailed line-by-line analysis."
        )
        return "\n".join(prompt_parts)
