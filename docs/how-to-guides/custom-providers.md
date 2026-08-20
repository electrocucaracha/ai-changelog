---
title: Add a Custom LLM Provider
parent: How-to guides
nav_order: 3
---

This guide shows how to register a custom LLM provider with AI Changelog Generator
so the tool routes model calls through your own backend without any changes to the upstream project.

Use this guide when you want to connect a provider that LiteLLM does not support natively,
such as a corporate AI gateway, a self-hosted inference server, or an internal proxy.

## How provider discovery works

AI Changelog Generator discovers custom LLM providers through the
[Python entry points](https://packaging.python.org/en/latest/specifications/entry-points/) mechanism.

When the tool starts, it looks for all packages installed in the active Python environment
that register an entry point under the `ai_changelog.litellm_providers` group.
Each discovered entry point is loaded and registered with LiteLLM's
[custom provider map](https://docs.litellm.ai/docs/providers/custom_provider)
before the first model call.

This means your provider handler lives entirely in your own package.
No Walmart-specific code, no gateway-specific code, and no credential material
ever needs to touch the upstream repository.

## Prerequisites

- Python 3.12 or later
- A LiteLLM-compatible custom handler class (see
  [LiteLLM custom provider documentation](https://docs.litellm.ai/docs/providers/custom_llm_server))
- A Python package that you can install alongside `ai-changelog`

## Steps

### 1. Create a custom handler class

Your handler must implement the `CustomLLM` interface from LiteLLM.
At minimum, implement the `completion` method.

```python
# src/mypackage/llm.py
from litellm import CustomLLM
from litellm.types.utils import ModelResponse


class Handler(CustomLLM):
    def completion(self, model: str, messages: list, **kwargs) -> ModelResponse:
        # Route the request to your backend here.
        ...
```

Refer to the
[LiteLLM custom provider documentation](https://docs.litellm.ai/docs/providers/custom_provider)
for the full interface, including async and streaming support.

### 2. Register the entry point

In your package's `pyproject.toml`, declare the entry point under the
`ai_changelog.litellm_providers` group.
The key is the provider prefix used in model strings.
The value is the dotted import path to your handler class.

```toml
[project.entry-points."ai_changelog.litellm_providers"]
my_provider = "mypackage.llm:Handler"
```

The key `my_provider` becomes the prefix in the model string.
For example, `my_provider/my-model-name` routes to your handler.

### 3. Install both packages

Install your package into the same Python environment as `ai-changelog`.

```bash
uv pip install ai-changelog ./path/to/your/package
```

If your package is published to a private registry,
add it via `uv pip install ai-changelog your-package`.

### 4. Run with your provider

Pass your provider prefix and model name via `--model`:

```bash
ai-changelog /path/to/repo --model my_provider/my-model-name
```

Or set the environment variable:

```bash
export CHANGELOG_MODEL=my_provider/my-model-name
ai-changelog /path/to/repo
```

## Behavior details

**Registration is idempotent.**
If `AIProvider` is instantiated more than once in the same process
(for example, during testing), a provider that is already registered is not added again.

**Failed providers do not block startup.**
If a registered entry point fails to load — for example because a dependency is missing —
the tool logs a warning and continues with the remaining providers.
This prevents a broken optional plugin from making the tool unusable.

**Provider registration order.**
Entry points are loaded in the order returned by `importlib.metadata.entry_points`,
which is determined by the Python environment's package installation order.
If two packages register the same provider name, the first one wins.

## Troubleshooting

**The tool uses the built-in provider instead of my handler.**
LiteLLM's native routing takes precedence over the custom provider map for its built-in
provider prefixes (`openai/`, `anthropic/`, `ollama/`, `azure/`, etc.).
Use a unique prefix that does not collide with any LiteLLM built-in provider.

**My handler is not being discovered.**
Verify the entry point is declared correctly by running:

```bash
python -c "from importlib.metadata import entry_points; print(list(entry_points(group='ai_changelog.litellm_providers')))"
```

An empty list means no packages have registered providers in the current environment.
Check that your package is installed and that the entry point group name is spelled correctly.

**I see a warning about a failed provider.**
Run with `--log-level DEBUG` to see the full error from the failed entry point:

```bash
ai-changelog /path/to/repo --log-level DEBUG --model my_provider/my-model
```

## Next

- Review all CLI options in [../references/index.md](../references/index.md)
- Read how the tool processes model calls in [../explanations/how-it-works.md](how-it-works.md)
