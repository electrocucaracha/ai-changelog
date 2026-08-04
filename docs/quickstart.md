# Quickstart

This quickstart gets you to a generated changelog in a few minutes.

## Prerequisites

- Python 3.9+
- uv
- A local Git repository with commits

## Run

From this project checkout:

```bash
uv run ai-changelog /path/to/repository
```

This command will:

1. Read commits from the target repository.
1. Generate AI summaries from commit diffs.
1. Store summaries in Git notes under the default namespace.
1. Create or update CHANGELOG.md.

## Verify

Check generated notes:

```bash
git -C /path/to/repository log --show-notes=refs/notes/ai-changelog
```

Check the changelog file:

```bash
cat /path/to/repository/CHANGELOG.md
```

## Run with GitHub Copilot provider (LiteLLM)

Use the GitHub Copilot provider model route:

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

On first request,
LiteLLM will prompt you for GitHub device-flow authentication.
Complete the URL and device-code verification shown in your terminal.

Optional token storage variables:

```bash
export GITHUB_COPILOT_TOKEN_DIR="~/.config/litellm/github_copilot"
export GITHUB_COPILOT_ACCESS_TOKEN_FILE="access-token"
export GITHUB_COPILOT_API_KEY_FILE="api-key.json"
```

## Next steps

- Review options in [cli-reference.md](cli-reference.md)
- Understand processing flow in [how-it-works.md](how-it-works.md)
