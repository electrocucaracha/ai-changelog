# AI Changelog Generator

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Super-Linter](https://github.com/electrocucaracha/ai-changelog/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

AI Changelog Generator is a tool designed to automate the creation of changelogs by generating AI-powered summaries of Git commit diffs. It simplifies the process of documenting changes in a repository by leveraging AI models to analyze commit histories and produce concise, meaningful summaries. These summaries are stored in Git notes and used to generate a `CHANGELOG.md` file in a structured format.

### What Problem Does It Solve?

Maintaining changelogs manually can be time-consuming and error-prone. This tool automates the process, ensuring that changelogs are consistent, up-to-date, and easy to understand. It supports multiple AI providers and integrates seamlessly with Git, making it a powerful solution for developers and teams.

## How to Use

### Requirements

- Python 3.9+
- `uv` (a Python task runner)

### Installation

Clone the repository and ensure you have the required dependencies installed. You can use the following command to activate the virtual environment:

```bash
source .venv/bin/activate
```

### Running the Tool

Run the tool directly from the repository:

```bash
uv run ai-changelog /path/to/repository
```

### Internal LiteLLM Gateway Routing

To route requests through an internal LiteLLM gateway while keeping project-level
autonomy over model selection and prompts, set optional gateway variables:

```bash
export CHANGELOG_LITELLM_API_BASE="https://your-internal-gateway.example/v1"
export CHANGELOG_LITELLM_API_KEY="<gateway-token>"
export CHANGELOG_LITELLM_HEADERS_JSON='{"X-Team":"developer-tools"}'
```

Then run the tool normally (or pass the equivalent CLI options).

### Using uvx

You can consume this tool with `uvx` in two common ways.

Git-direct method with environment variables:

```bash
export CHANGELOG_MODEL=gpt-4o-mini
export CHANGELOG_LITELLM_API_BASE="https://your-internal-gateway.example/v1"
export CHANGELOG_LITELLM_API_KEY="<gateway-token>"
export CHANGELOG_LITELLM_HEADERS_JSON='{"X-Team":"developer-tools"}'

uvx --from "git+https://github.com/electrocucaracha/ai-changelog.git" \
  ai-changelog /path/to/repository
```

Local checkout method:

uvx --from . ai-changelog /path/to/repository

If your environment requires private index resolution for your model gateway
client dependencies, configure your `uv` index/sources in `pyproject.toml`
(or your org-standard `uv` configuration) before invoking `uvx`.

### Options

- `--model`: Specify the AI model (default: ollama/llama3.1)
- `--namespace`: Git notes namespace (default: ai-changelog)
- `--force`: Re-generate summaries for commits that already have notes
- `--clear-all`: Remove all notes from the selected namespace and exit
- `--create-semver-tags`: Create semantic version tags if none exist
- `--limit`: Process only the last N commits
- `--log-level`: Set logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `--changelog-file`: Specify the output path for the changelog (default: `CHANGELOG.md`)
- `--litellm-api-base`: Optional internal LiteLLM gateway base URL
- `--litellm-api-key`: Optional API key for gateway authentication
- `--litellm-headers-json`: Optional JSON object with request headers for gateway routing or policy metadata

### Viewing Git Notes

Summaries are stored in Git notes under the namespace `ai-changelog`. To view them, use:

```bash
git log --show-notes=refs/notes/ai-changelog
```

## Features

- Multi-provider AI support via LiteLLM (Claude, OpenAI, local models, etc.)
- Git notes integration for persistent, non-intrusive storage
- Batch processing of all commits in repository history
- Customizable summaries with configurable prompts
- Automatic changelog generation from Git notes and commit history
- Error handling and retry logic

## How It Works

1. **Repository Scanning**: Walks through all commits in the repository.
2. **Diff Analysis**: Extracts and analyzes file changes for each commit.
3. **Summary Generation**: Uses the configured AI model to create concise summaries.
4. **Notes Storage**: Stores summaries in Git notes (non-invasive, doesn't alter commit history).
5. **Tag Generation**: Optionally creates semantic version tags from git-note categories.
6. **Changelog Rendering**: Builds a changelog using generated notes and semantic version tags, appending only missing release sections when `CHANGELOG.md` already exists.

## Contributing

Follow the code style and include appropriate error handling for all new features. Development and test workflow details, including Deepeval summarization checks, are documented in `CONTRIBUTING.md`.
