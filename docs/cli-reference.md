# CLI Reference

## Usage

```bash
uv run ai-changelog /path/to/repository [options]
```

## Common options

- --model: AI model name. Default is ollama/llama3.1.
- --namespace: Git notes namespace. Default is ai-changelog.
- --force: Regenerate summaries even when notes already exist.
- --clear-all: Delete all notes in the selected namespace and exit.
- --create-semver-tags: Create semantic version tags when missing.
- --limit: Process only the most recent N commits.
- --log-level: Set log verbosity.
- --changelog-file: Output path for changelog. Default is CHANGELOG.md.

## LiteLLM gateway options

- --litellm-api-base: Gateway base URL.
- --litellm-api-key: Gateway API key.
- --litellm-headers-json: JSON object of additional request headers.

## Environment variables

All CLI options can be configured through environment variables.
CLI arguments and flags still take precedence over environment values.

- --model -> CHANGELOG_MODEL
- --namespace -> CHANGELOG_NAMESPACE
- --force -> CHANGELOG_FORCE
- --clear-all -> CHANGELOG_CLEAR_ALL
- --create-semver-tags -> CHANGELOG_CREATE_SEMVER_TAGS
- --limit -> CHANGELOG_LIMIT
- --log-level -> CHANGELOG_LOG_LEVEL
- --changelog-file -> CHANGELOG_CHANGELOG_FILE
- --litellm-api-base -> CHANGELOG_LITELLM_API_BASE
- --litellm-api-key -> CHANGELOG_LITELLM_API_KEY
- --litellm-headers-json -> CHANGELOG_LITELLM_HEADERS_JSON

## Example

```bash
CHANGELOG_MODEL=gpt-4o-mini \
CHANGELOG_NAMESPACE=ai-changelog \
CHANGELOG_FORCE=1 \
CHANGELOG_LITELLM_API_BASE="https://your-internal-gateway.example/v1" \
CHANGELOG_LITELLM_API_KEY="<gateway-token>" \
CHANGELOG_LITELLM_HEADERS_JSON='{"X-Team":"developer-tools"}' \
uv run ai-changelog /path/to/repository --limit 100
```

## GitHub Copilot provider example

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

First run uses GitHub device-flow authentication through LiteLLM.
