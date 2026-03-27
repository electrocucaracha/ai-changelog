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

import os
from dataclasses import dataclass
from typing import Sequence
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from ai_changelog_msg.ai_provider import AIProvider
from ai_changelog_msg.config import Config


def _enabled() -> bool:
    return os.getenv("AI_CHANGELOG_DEEPEVAL_RUN", "0") == "1"


pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not _enabled(),
        reason="Set AI_CHANGELOG_DEEPEVAL_RUN=1 to enable live deepeval checks",
    ),
]


@dataclass(frozen=True)
class SummarizationEvalCase:
    name: str
    commit_message: str
    diff: str
    author: str
    assessment_questions: Sequence[str]


EVAL_CASES = (
    SummarizationEvalCase(
        name="cli option addition",
        commit_message="feat(cli): support custom changelog output path",
        author="Alice",
        diff="""
diff --git a/src/ai_changelog_msg/main.py b/src/ai_changelog_msg/main.py
index 1111111..2222222 100644
--- a/src/ai_changelog_msg/main.py
+++ b/src/ai_changelog_msg/main.py
@@
+@click.option(
+    \"--changelog-file\",
+    default=\"CHANGELOG.md\",
+    help=\"Write the generated changelog to a custom file path\",
+)
 def cli(...):
-    changelog_file = \"CHANGELOG.md\"
+    changelog_file = changelog_file
""".strip(),
        assessment_questions=(
            "Does the summary mention a new CLI option?",
            "Does the summary mention choosing a custom changelog output path?",
        ),
    ),
    SummarizationEvalCase(
        name="empty diff handling",
        commit_message="fix(ai): avoid calling the model for empty diffs",
        author="Bob",
        diff="""
diff --git a/src/ai_changelog_msg/ai_provider.py b/src/ai_changelog_msg/ai_provider.py
index 3333333..4444444 100644
--- a/src/ai_changelog_msg/ai_provider.py
+++ b/src/ai_changelog_msg/ai_provider.py
@@
+        if not diff.strip():
+            return \"[No changes to summarize]\"

         prompt = self._build_prompt(commit_message, diff, author)
         response = litellm.completion(...)
""".strip(),
        assessment_questions=(
            "Does the summary mention handling empty diffs?",
            "Does the summary indicate the model call is skipped or avoided when there are no changes?",
        ),
    ),
    SummarizationEvalCase(
        name="legacy note normalization",
        commit_message="fix(changelog): normalize legacy notes before rendering",
        author="Carol",
        diff="""
diff --git a/src/ai_changelog_msg/main.py b/src/ai_changelog_msg/main.py
index 5555555..6666666 100644
--- a/src/ai_changelog_msg/main.py
+++ b/src/ai_changelog_msg/main.py
@@
-        note_text = existing_note
+        normalized_category = category or "Changed"
+        note_text = format_note(normalized_category, existing_note, is_breaking)

         repo.set_note(commit.hexsha, note_text, namespace)
""".strip(),
        assessment_questions=(
            "Does the summary mention legacy notes being normalized?",
            "Does the summary mention note formatting or rendering consistency improvements?",
        ),
    ),
)


def _ollama_available(base_url: str) -> bool:
    try:
        with urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=3) as response:
            return response.status == 200  # type: ignore[no-any-return]
    except (OSError, URLError):
        return False


def _judge_model_name() -> str:
    model_name = os.getenv("AI_CHANGELOG_DEEPEVAL_JUDGE_MODEL", "llama3.1")
    return model_name.removeprefix("ollama/")


@pytest.fixture(scope="module")
def deepeval_components():
    deepeval = pytest.importorskip("deepeval")
    pytest.importorskip("ollama")
    metrics = pytest.importorskip("deepeval.metrics")
    models = pytest.importorskip("deepeval.models")
    test_case_module = pytest.importorskip("deepeval.test_case")
    return deepeval, metrics, models, test_case_module


@pytest.fixture(scope="module")
def ollama_base_url() -> str:
    base_url = os.getenv("AI_CHANGELOG_DEEPEVAL_BASE_URL", "http://localhost:11434")
    if not _ollama_available(base_url):
        pytest.skip(f"Ollama is not reachable at {base_url}")
    return base_url


@pytest.fixture(scope="module")
def provider(ollama_base_url: str) -> AIProvider:
    os.environ.setdefault("OLLAMA_API_BASE", ollama_base_url)
    return AIProvider(Config(model=os.getenv("CHANGELOG_MODEL", "ollama/llama3.1")))


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda case: case.name)
def test_commit_diff_summaries_score_above_threshold(
    case: SummarizationEvalCase,
    provider: AIProvider,
    ollama_base_url: str,
    deepeval_components,
):
    _, metrics, models, test_case_module = deepeval_components

    summary = provider.summarize_diff(case.commit_message, case.diff, case.author)
    input_text = provider._build_prompt(case.commit_message, case.diff, case.author)
    threshold = float(os.getenv("AI_CHANGELOG_DEEPEVAL_THRESHOLD", "0.5"))

    metric = metrics.SummarizationMetric(
        threshold=threshold,
        model=models.OllamaModel(
            model=_judge_model_name(),
            base_url=ollama_base_url,
            temperature=0,
        ),
        assessment_questions=list(case.assessment_questions),
        include_reason=True,
        async_mode=False,
    )
    test_case = test_case_module.LLMTestCase(
        input=input_text,
        actual_output=summary,
    )

    metric.measure(test_case)

    assert metric.score >= threshold, (
        f"summary={summary!r}\n"
        f"score={metric.score}\n"
        f"reason={metric.reason}\n"
        f"breakdown={getattr(metric, 'score_breakdown', None)}"
    )
