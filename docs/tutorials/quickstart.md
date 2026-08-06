# Quickstart

This quickstart gets you to a generated changelog in a few minutes.

## Prerequisites

- Python 3.9+
- uv
- A local Git repository with commits

## Ollama requirements (default setup)

By default,
this project uses an Ollama-backed LiteLLM model route.
To run with defaults,
ensure all of the following are true:

- Ollama is installed and running locally.
- Ollama HTTP API is reachable at `http://localhost:11434`.
- The default model is available,
  or can be pulled automatically on first run.

Default values used by the CLI:

- `CHANGELOG_MODEL`:
  - `ollama/llama3.1:8b-instruct-q4_K_M` on Apple Silicon macOS.
  - `ollama/llama3.1` on other platforms.
- `CHANGELOG_NAMESPACE`: `ai-changelog`
- `CHANGELOG_RETRY_ATTEMPTS`: `3`
- `CHANGELOG_RETRY_BACKOFF_SECONDS`: `1.0`

Quick verification commands:

```bash
ollama --version
ollama ps
curl -fsS http://localhost:11434/api/tags
```

If Ollama is not running yet,
start it and pre-pull the default model for your platform:

```bash
ollama serve
# In another terminal:
ollama pull llama3.1:8b-instruct-q4_K_M   # Apple Silicon macOS
ollama pull llama3.1                       # Other platforms
```

## Configure Git notes sync

AI summaries are stored in Git notes under refs/notes/ai-changelog.
Configure your repository so pull and fetch operations include that notes ref.

```ini
[remote "origin"]
  fetch = +refs/heads/*:refs/remotes/origin/
  fetch = +refs/notes/ai-changelog:refs/notes/ai-changelog
```

You can set this using Git commands:

```bash
git config --add remote.origin.fetch '+refs/notes/ai-changelog:refs/notes/ai-changelog'
git fetch origin
```

## Scenario 1: Bootstrap from an existing project

From the root of your target repository,
run ai-changelog directly from GitHub:

```bash
uvx --from git+https://github.com/electrocucaracha/ai-changelog.git ai-changelog .
```

Commit and push the generated changelog changes:

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): update release notes"
git push origin HEAD
```

Push the Git notes namespace so teammates and CI can reuse summaries:

```bash
git push origin refs/notes/ai-changelog
```

## Scenario 2: Update an already configured project

1. Ensure your repository fetches ai-changelog notes from origin.
1. Pull code and notes.
1. Run ai-changelog.
1. Push both regular commits and notes updates.

Configure fetch once if needed:

```bash
git config --add remote.origin.fetch '+refs/notes/ai-changelog:refs/notes/ai-changelog'
```

Update local repository state:

```bash
git pull --ff-only
git fetch origin refs/notes/ai-changelog:refs/notes/ai-changelog
```

Run ai-changelog from the project checkout:

```bash
uv run ai-changelog .
```

Commit and push changelog updates:

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): update release notes"
git push origin HEAD
```

Push updated notes:

```bash
git push origin refs/notes/ai-changelog
```

## Run from this project checkout

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

- Review options in [../references/cli-reference.md](../references/cli-reference.md)
- Understand processing flow in [../explanations/how-it-works.md](../explanations/how-it-works.md)
- Configure automated releases in [../how-to-guides/github-actions-release.md](../how-to-guides/github-actions-release.md)
