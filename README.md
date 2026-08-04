# AI Changelog Generator

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Super-Linter](https://github.com/electrocucaracha/ai-changelog/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

AI Changelog Generator automates release-note creation from Git history.
It analyzes commit diffs with an AI model,
stores per-commit summaries in Git notes,
and renders a structured CHANGELOG.md.

### What Problem Does It Solve

Writing changelogs by hand is repetitive,
easy to delay,
and often inconsistent across releases.
This project solves that by generating changelog content directly from commits,
so release notes are faster to produce and easier to keep accurate.

## Core Features

- AI-powered summaries generated from commit diffs
- Git notes storage that does not rewrite history
- Multi-provider support through LiteLLM
- Changelog rendering with semantic version release sections
- Optional semantic tag creation when tags are missing

## Quick Start

Requirements:

- Python 3.9+
- uv

Run:

```bash
uv run ai-changelog /path/to/repository
```

All CLI flags can also be supplied through environment variables.
See [docs/cli-reference.md](docs/cli-reference.md#environment-variables) for the full mapping.

### Run with LiteLLM GitHub Copilot provider

Set the model to the GitHub Copilot provider route:

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

On first run,
LiteLLM will start the GitHub device authentication flow.
Follow the verification URL and device code prompt in your terminal.

Optional token storage customization:

```bash
export GITHUB_COPILOT_TOKEN_DIR="~/.config/litellm/github_copilot"
export GITHUB_COPILOT_ACCESS_TOKEN_FILE="access-token"
export GITHUB_COPILOT_API_KEY_FILE="api-key.json"
```

## Documentation

- Project docs site: [docs/index.md](docs/index.md)
- Quickstart: [docs/quickstart.md](docs/quickstart.md)
- CLI options: [docs/cli-reference.md](docs/cli-reference.md)
- Processing flow: [docs/how-it-works.md](docs/how-it-works.md)

## Contributing

Follow the code style and include appropriate error handling for all new features. Development and test workflow details, including Deepeval summarization checks, are documented in `CONTRIBUTING.md`.
