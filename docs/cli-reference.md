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
- --workers: Maximum worker threads for AI summarization.
- --retry-attempts: Max retry attempts for transient AI API failures. Default is 3.
- --retry-backoff-seconds: Base retry delay in seconds. Default is 1.0.
- --log-level: Set log verbosity.
- --changelog-file: Output path for changelog. Default is CHANGELOG.md.

## LiteLLM gateway options

- --litellm-api-base: Optional API base override for this run.
- --litellm-api-key: Optional API key override for this run.
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
- --workers -> CHANGELOG_WORKERS
- --retry-attempts -> CHANGELOG_RETRY_ATTEMPTS
- --retry-backoff-seconds -> CHANGELOG_RETRY_BACKOFF_SECONDS
- --log-level -> CHANGELOG_LOG_LEVEL
- --changelog-file -> CHANGELOG_CHANGELOG_FILE
- --litellm-headers-json -> CHANGELOG_LITELLM_HEADERS_JSON
- (optional) enable Headroom callback -> CHANGELOG_ENABLE_HEADROOM

LiteLLM-native environment variables are preferred for authentication and provider routing.
The application passes model/provider resolution to LiteLLM,
so set provider credentials directly in your shell.

Common provider-specific key variables:

- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- XAI_API_KEY
- TOGETHERAI_API_KEY
- REPLICATE_API_KEY
- FIREWORKS_AI_API_KEY
- LITELLM_PROXY_API_KEY

Optional compression-specific variable:

- CHANGELOG_ENABLE_HEADROOM (true/false, defaults to true)

Common base/version variables:

- OPENAI_BASE_URL
- AZURE_API_BASE
- AZURE_API_VERSION
- AZURE_API_TYPE

Cloud/provider context variables supported by LiteLLM include:

- azure_ad_token
- vertex_project
- vertex_location
- aws_region_name
- project
- region_name
- token

## Example

```bash
CHANGELOG_MODEL=gpt-4o-mini \
CHANGELOG_NAMESPACE=ai-changelog \
CHANGELOG_FORCE=1 \
OPENAI_BASE_URL="https://your-internal-gateway.example/v1" \
OPENAI_API_KEY="<provider-or-gateway-token>" \
CHANGELOG_LITELLM_HEADERS_JSON='{"X-Team":"developer-tools"}' \
uv run ai-changelog /path/to/repository --limit 100
```

## GitHub Copilot provider example

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

First run uses GitHub device-flow authentication through LiteLLM.
