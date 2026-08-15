---
title: GitHub Actions Release Setup
parent: How-to guides
nav_order: 2
---

This guide shows how to run AI Changelog Generator in GitHub Actions,
write a new release entry into CHANGELOG.md,
and publish a GitHub Release with softprops/action-gh-release.

Use this guide when you want a manual,
auditable release flow from your repository UI.

## What this workflow does

The workflow at .github/workflows/release.yml performs these steps:

1. Checks out the repository with full history.
1. Fetches and later pushes refs/notes/ai-changelog so AI summaries persist.
1. Runs ai-changelog to regenerate CHANGELOG.md.
1. Commits and pushes CHANGELOG.md to master.
1. Creates and pushes a release tag.
1. Publishes the release using CHANGELOG.md as the release body.

## YAML sample

Use this minimal sample as a starting point.
It runs ai-changelog,
commits CHANGELOG.md,
and publishes a release using CHANGELOG.md as release notes.

```yaml
name: Release with AI Changelog

on:
    workflow_dispatch:
        inputs:
            model:
                description: Optional model override
                required: false
                default: ""
                type: string

permissions:
    contents: write

jobs:
    release:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
                with:
                    fetch-depth: 0
                    token: ${{ secrets.WORKFLOW_TOKEN }}

            - run: git fetch origin refs/notes/ai-changelog:refs/notes/ai-changelog || true

            - uses: astral-sh/setup-uv@v9

            - uses: actions/setup-python@v5
                with:
                    python-version-file: pyproject.toml

            - name: Generate CHANGELOG.md
                env:
                    CHANGELOG_MODEL: ${{ inputs.model != '' && inputs.model || vars.CHANGELOG_MODEL }}
                    GITHUB_API_KEY: ${{ secrets.GITHUB_API_KEY }}
                run: uv run ai-changelog . --force --create-semver-tags --changelog-file CHANGELOG.md

            - name: Commit and push changelog
                uses: actions-js/push@master
                with:
                    github_token: ${{ secrets.WORKFLOW_TOKEN }}
                    branch: master
                    message: "docs(changelog): update release notes"
                    tags: true

            - name: Push notes and tags
                run: git push origin refs/notes/ai-changelog || true

            - name: Resolve latest semantic tag
                id: release_tag
                run: |
                    TAG="$(git tag --sort=-v:refname | head -n 1)"
                    if [ -z "$TAG" ]; then
                        echo "No semantic version tag found after changelog generation"
                        exit 1
                    fi
                    echo "tag=$TAG" >> "$GITHUB_OUTPUT"

            - uses: softprops/action-gh-release@v2
                with:
                    tag_name: ${{ steps.release_tag.outputs.tag }}
                    body_path: CHANGELOG.md
                    token: ${{ secrets.WORKFLOW_TOKEN }}
```

In this version,
ai-changelog creates semantic tags automatically with --create-semver-tags,
and the workflow publishes a release for the latest generated semantic tag.

The sample uses a GitHub push action for branch updates,
then explicitly pushes the ai-changelog notes ref in a separate step.

For readability,
the sample keeps only one provider credential.
If you use another route,
replace GITHUB_API_KEY with the single key your model needs
(for example OPENAI_API_KEY,
ANTHROPIC_API_KEY,
GITHUB_COPILOT_API_KEY,
or LITELLM_PROXY_API_KEY).

Tip:
for this repository,
the production-ready workflow is the tracked file at .github/workflows/release.yml.

## Prerequisites

Before running the workflow,
configure your repository settings.

### Required secret

- WORKFLOW_TOKEN

This token must have write access to repository contents,
including tags and releases.

### Model configuration

Set one of these approaches:

1. Set repository variable CHANGELOG_MODEL,
   for example github/Phi-4.
1. Or provide the model input when manually dispatching the workflow.

### Provider credentials

Set the credentials needed by your selected model route.

Common options include:

- GITHUB_API_KEY
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- XAI_API_KEY
- TOGETHERAI_API_KEY
- REPLICATE_API_KEY
- FIREWORKS_AI_API_KEY
- LITELLM_PROXY_API_KEY

Optional base URL variable:

- OPENAI_BASE_URL (repository variable)

## GitHub Copilot setup options

If you choose github_copilot/\* models,
prefer a non-interactive authentication strategy for CI.

### Option A: LiteLLM proxy (recommended for CI)

1. Set CHANGELOG_MODEL to github_copilot/gpt-4 (or another github_copilot/\* model).
1. Set LITELLM_PROXY_API_KEY in repository secrets.
1. Point LiteLLM routing to your proxy endpoint using your existing provider config.

This avoids device-flow prompts during workflow execution.

### Option B: Direct Copilot variables

The workflow also supports direct Copilot variables:

- GITHUB_COPILOT_API_KEY (secret)
- GITHUB_COPILOT_API_BASE (variable, optional)
- GITHUB_COPILOT_DEVICE_CODE_URL (variable, optional)
- GITHUB_COPILOT_ACCESS_TOKEN_URL (variable, optional)
- GITHUB_COPILOT_API_KEY_URL (variable, optional)

Note:
some direct Copilot setups may still require first-time device-flow auth,
which is not suitable for non-interactive runners.

## Run a release

1. Open the Actions tab in GitHub.
1. Select Release with AI Changelog.
1. Click Run workflow.
1. Optionally enter a model override.

After completion,
you will see:

- A CHANGELOG.md update committed to master.
- A pushed Git tag.
- A GitHub Release created from CHANGELOG.md.

## Verify results

Review these artifacts:

1. Commit history for the docs(changelog) commit.
1. GitHub Releases page for the new release entry.
1. CHANGELOG.md for the new version section.

The release body is the full changelog file.
If you prefer a single-version section only,
add a pre-step that extracts one section into a temporary file.

## Troubleshooting

### No changelog update was committed

The workflow exits early when CHANGELOG.md has no diff.
This is expected when generated output did not change.

### Release created but notes section missing

Ensure the tag format matches your changelog section,
for example tag v1.2.3 should match section [1.2.3].

### Copilot model fails in CI

Use the LiteLLM proxy option with LITELLM_PROXY_API_KEY,
or switch to another non-interactive provider route.
