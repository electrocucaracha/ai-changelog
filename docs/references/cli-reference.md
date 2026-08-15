---
title: CLI Reference
parent: References
nav_order: 1
---

## Command

```bash
uv run ai-changelog /path/to/repository [options]
```

`/path/to/repository` is required.
It must point to the Git repository you want to analyze.

## Common Options

| Option                    | Env var                           | Default                | Description                                             |
| ------------------------- | --------------------------------- | ---------------------- | ------------------------------------------------------- |
| `--model`                 | `CHANGELOG_MODEL`                 | `ollama/llama3.1`      | AI model name passed to LiteLLM.                        |
| `--namespace`             | `CHANGELOG_NAMESPACE`             | `ai-changelog`         | Git notes namespace used to store per-commit summaries. |
| `--force`                 | `CHANGELOG_FORCE`                 | `false`                | Regenerate summaries even when notes already exist.     |
| `--clear-all`             | `CHANGELOG_CLEAR_ALL`             | `false`                | Delete all notes in the selected namespace and exit.    |
| `--create-semver-tags`    | `CHANGELOG_CREATE_SEMVER_TAGS`    | `false`                | Create semantic version tags when missing.              |
| `--limit`                 | `CHANGELOG_LIMIT`                 | unset                  | Process only the most recent `N` commits.               |
| `--workers`               | `CHANGELOG_WORKERS`               | implementation-defined | Maximum worker threads for AI summarization.            |
| `--retry-attempts`        | `CHANGELOG_RETRY_ATTEMPTS`        | `3`                    | Retry attempts for transient AI API failures.           |
| `--retry-backoff-seconds` | `CHANGELOG_RETRY_BACKOFF_SECONDS` | `1.0`                  | Base retry delay in seconds.                            |
| `--overall-progress-mode` | `CHANGELOG_OVERALL_PROGRESS_MODE` | `commits`              | Overall progress counting mode.                         |
| `--log-level`             | `CHANGELOG_LOG_LEVEL`             | implementation-defined | Log verbosity level.                                    |
| `--changelog-file`        | `CHANGELOG_CHANGELOG_FILE`        | `CHANGELOG.md`         | Output path for generated changelog content.            |

### Progress Mode Values

- `commits`: Count each commit once.
- `work-units`: Count summary generation and commit processing separately.

## LiteLLM Gateway Options

- `--litellm-api-base`: Optional API base override for the current run.
- `--litellm-api-key`: Optional API key override for the current run.
- `--litellm-headers-json`: JSON object of additional request headers.

`--litellm-headers-json` maps to `CHANGELOG_LITELLM_HEADERS_JSON`.

## Environment Variables

All CLI options can be configured through environment variables.
CLI arguments and flags still take precedence over environment values.

- `--model` -> `CHANGELOG_MODEL`
- `--namespace` -> `CHANGELOG_NAMESPACE`
- `--force` -> `CHANGELOG_FORCE`
- `--clear-all` -> `CHANGELOG_CLEAR_ALL`
- `--create-semver-tags` -> `CHANGELOG_CREATE_SEMVER_TAGS`
- `--limit` -> `CHANGELOG_LIMIT`
- `--workers` -> `CHANGELOG_WORKERS`
- `--retry-attempts` -> `CHANGELOG_RETRY_ATTEMPTS`
- `--retry-backoff-seconds` -> `CHANGELOG_RETRY_BACKOFF_SECONDS`
- `--overall-progress-mode` -> `CHANGELOG_OVERALL_PROGRESS_MODE`
- `--log-level` -> `CHANGELOG_LOG_LEVEL`
- `--changelog-file` -> `CHANGELOG_CHANGELOG_FILE`
- `--litellm-headers-json` -> `CHANGELOG_LITELLM_HEADERS_JSON`
- Optional Headroom callback toggle -> `CHANGELOG_ENABLE_HEADROOM`

LiteLLM-native environment variables are preferred for authentication and provider routing.
The application passes model/provider resolution to LiteLLM,
so set provider credentials directly in your shell.

### Common Provider Key Variables

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `XAI_API_KEY`
- `TOGETHERAI_API_KEY`
- `REPLICATE_API_KEY`
- `FIREWORKS_AI_API_KEY`
- `LITELLM_PROXY_API_KEY`

### Optional Compression Variable

- `CHANGELOG_ENABLE_HEADROOM` (`true` or `false`, defaults to `true`)

### Common Base Or Version Variables

- `OPENAI_BASE_URL`
- `AZURE_API_BASE`
- `AZURE_API_VERSION`
- `AZURE_API_TYPE`

Cloud/provider context variables supported by LiteLLM include:

- `azure_ad_token`
- `vertex_project`
- `vertex_location`
- `aws_region_name`
- `project`
- `region_name`
- `token`

## Examples

### Run Against Recent Commits

```bash
CHANGELOG_MODEL=gpt-4o-mini \
CHANGELOG_NAMESPACE=ai-changelog \
CHANGELOG_FORCE=1 \
OPENAI_BASE_URL="https://your-internal-gateway.example/v1" \
OPENAI_API_KEY="<provider-or-gateway-token>" \
CHANGELOG_LITELLM_HEADERS_JSON='{"X-Team":"developer-tools"}' \
uv run ai-changelog /path/to/repository --limit 100
```

### Use GitHub Copilot Through LiteLLM

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

On first run, LiteLLM uses GitHub device-flow authentication.

### Clear Existing Notes For A Namespace

```bash
uv run ai-changelog /path/to/repository --namespace ai-changelog --clear-all
```

This command deletes notes in the selected namespace and exits.
