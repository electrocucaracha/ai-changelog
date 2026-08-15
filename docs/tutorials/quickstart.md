---
title: Generate your first commit message
parent: Tutorials
nav_order: 1
---

# Quickstart

This quickstart gets you to a generated changelog in a few minutes.

## Prerequisites

- Python 3.9+
- uv
- A local Git repository with commits

## Set up Ollama (default provider)

By default,
ai-changelog uses an Ollama-backed LiteLLM model route.
Ensure all of the following are true before you continue:

- Ollama is installed and running locally.
- The Ollama HTTP API is reachable at `http://localhost:11434`.
- The default model is available.

Default model per platform:

- Apple Silicon macOS: `ollama/llama3.1:8b-instruct-q4_K_M`
- Other platforms: `ollama/llama3.1`

Verify Ollama is running:

```bash
ollama --version
ollama ps
curl -fsS http://localhost:11434/api/tags
```

If Ollama is not running,
start it and pull the default model for your platform:

```bash
ollama serve
# In another terminal:
ollama pull llama3.1:8b-instruct-q4_K_M   # Apple Silicon macOS
ollama pull llama3.1                       # Other platforms
```

## Configure Git notes fetch (one-time setup)

ai-changelog stores AI summaries in Git notes under `refs/notes/ai-changelog`.
Add the notes ref to your remote fetch configuration
so pull and fetch operations include it:

```bash
git config --add remote.origin.fetch '+refs/notes/ai-changelog:refs/notes/ai-changelog'
git fetch origin
```

Or add it directly in `.git/config`:

```ini
[remote "origin"]
  fetch = +refs/heads/*:refs/remotes/origin/
  fetch = +refs/notes/ai-changelog:refs/notes/ai-changelog
```

## Scenario 1: Bootstrap a new project

From the root of your target repository,
run ai-changelog directly from GitHub:

```bash
uvx --from git+https://github.com/electrocucaracha/ai-changelog.git ai-changelog .
```

Commit and push the generated changelog and AI notes:

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): update release notes"
git push origin HEAD
git push origin refs/notes/ai-changelog
```

## Scenario 2: Update an already configured project

Pull the latest code and notes:

```bash
git pull --ff-only
git fetch origin refs/notes/ai-changelog:refs/notes/ai-changelog
```

Run ai-changelog:

```bash
uv run ai-changelog .
```

Commit and push the changelog and updated notes:

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): update release notes"
git push origin HEAD
git push origin refs/notes/ai-changelog
```

## Verify

Check that summaries were stored in Git notes:

```bash
git -C /path/to/repository log --show-notes=refs/notes/ai-changelog
```

Check the generated changelog:

```bash
cat /path/to/repository/CHANGELOG.md
```

## Run from this project's source

If you have cloned this repository,
run ai-changelog against any local repository path:

```bash
uv run ai-changelog /path/to/repository
```

The command reads commits from the target repository,
generates AI summaries from commit diffs,
stores summaries in Git notes under the default namespace,
and creates or updates `CHANGELOG.md`.

## Use the GitHub Copilot provider

Set the model to a `github_copilot/` route to use GitHub Copilot instead of Ollama:

```bash
export CHANGELOG_MODEL="github_copilot/gpt-4"
uv run ai-changelog /path/to/repository
```

On first request,
LiteLLM prompts you for GitHub device-flow authentication.
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
