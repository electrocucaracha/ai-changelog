---
title: Home
nav_order: 1
---

# AI Changelog Generator

AI Changelog Generator creates release notes from your Git history using AI.
It analyzes commit diffs, writes commit summaries into Git notes,
and renders a structured CHANGELOG.md from those summaries.

## Why this exists

Teams often postpone changelog updates because writing them is repetitive.
Manual changelog writing also causes inconsistent tone,
missing entries,
and low confidence in release notes.

This project solves that by automating changelog generation while keeping data inside your repository.

## What you get

- AI-powered summaries per commit diff
- Git notes storage that does not rewrite commit history
- Changelog generation grouped by semantic version tags
- Optional semantic version tag creation when tags are missing
- Support for multiple AI providers through LiteLLM

## How it works

1. Scan commits in a repository.
1. Generate a summary for each commit diff.
1. Store summaries in a Git notes namespace.
1. Build or append release sections in CHANGELOG.md.

## Quickstart

Prerequisites:

- Python 3.9+
- uv

Run from your checkout:

```bash
uv run ai-changelog /path/to/repository
```

The quickstart guide also includes two operational workflows:

- Bootstrap from an existing repository using uvx.
- Update an existing repository with Git notes fetch and push sync.

See [tutorials/quickstart.md](tutorials/quickstart.md) for full command sequences.

## Configuration highlights

- Every CLI option supports an environment-variable equivalent.
- Full flag-to-environment mapping: [references/cli-reference.md](references/cli-reference.md#environment-variables)
- Optional LiteLLM provider and gateway configuration via native LiteLLM env vars,
  such as OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
  OPENAI_BASE_URL, and AZURE_API_BASE.
- Optional per-request custom headers via CHANGELOG_LITELLM_HEADERS_JSON.

## Docs by type

- Tutorials: [tutorials/index.md](tutorials/index.md)
- How-to guides: [how-to-guides/index.md](how-to-guides/index.md)
- References: [references/index.md](references/index.md)
- Explanations: [explanations/index.md](explanations/index.md)

For GitHub Copilot via LiteLLM,
see the Quickstart section "Run with GitHub Copilot provider (LiteLLM)".
