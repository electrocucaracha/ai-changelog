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

## Configuration highlights

- Every CLI option supports an environment-variable equivalent.
- Full flag-to-environment mapping: [cli-reference.md](cli-reference.md#environment-variables)
- Optional internal LiteLLM gateway via:
  - CHANGELOG_LITELLM_API_BASE
  - CHANGELOG_LITELLM_API_KEY
  - CHANGELOG_LITELLM_HEADERS_JSON

## Docs map

- Quickstart: [quickstart.md](quickstart.md)
- Command options: [cli-reference.md](cli-reference.md)
- Changelog flow details: [how-it-works.md](how-it-works.md)

For GitHub Copilot via LiteLLM,
see the Quickstart section "Run with GitHub Copilot provider (LiteLLM)".
