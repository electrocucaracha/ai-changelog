# How It Works

AI Changelog Generator automates release note creation by combining Git history with an AI model.
It reads every commit in your repository,
uses a language model to produce a human-readable summary of the diff,
stores the summary and a precomputed changelog entry as Git notes,
and then renders them into a structured `CHANGELOG.md` grouped by semantic version release.

The pipeline has six logical stages.
Commit preparation and final rendering run in a deterministic order,
while AI generation runs concurrently and persists each completed result immediately.

![AI Changelog Generator pipeline diagram](how-it-works.drawio.png)

## 1. Repository scanning

The tool opens the target Git repository using [GitPython](https://gitpython.readthedocs.io/)
and walks commit history from `HEAD` backward, newest-first.

You can process the full history or cap the run to the most recent commits with `--limit`.
Capping is useful for large repositories or for incremental runs when you only want to
annotate commits added since the last execution.

> Note: `--limit` is incompatible with `--create-semver-tags`
> because partial history produces incorrect version numbers.

## 2. Diff extraction

For each commit the tool fetches a unified diff:

- **Normal commits** — diff is computed against the first parent commit.
- **Root commit** — `git show` is used so all initially added files appear.

Diffs larger than `max_diff_size` (default 50 000 characters) are truncated before
being sent to the model to stay within context-window limits.

## 3. AI summary generation

Each diff is forwarded to the configured language model through
[LiteLLM](https://docs.litellm.ai/),
which provides a single interface to Ollama, OpenAI, Anthropic, and any other
LiteLLM-compatible model.

For every new commit, the model produces a detailed Git-note summary
and a one-sentence [Keep a Changelog](https://keepachangelog.com/) entry.
The tool assigns the entry to `Added`, `Changed`, `Fixed`, or `Removed`.
Both values are created while the commit is processed,
so the final rendering stage does not make additional model calls.

Summaries and entries are generated **concurrently** using a `ThreadPoolExecutor`.
The number of worker threads defaults to the host's CPU count
but can be overridden with `--workers`.
The CLI renders a per-worker progress bar during the run.

The coordinator receives completed worker results as they become available.
It writes each successful result as a Git note before handling the next completed result,
so Git updates remain single-threaded while model requests continue in parallel.

Transient failures (timeouts, rate-limit 429s, 5xx errors) are retried with
exponential back-off controlled by `--retry-attempts` and `--retry-backoff-seconds`.

When a commit already has a note in the target namespace and `--force` is not supplied,
the AI call is skipped and the existing note is reused.
This makes incremental runs cheap.

## 4. Git notes storage

Each generated summary and changelog entry are persisted as a
[Git note](https://git-scm.com/docs/git-notes)
under a dedicated namespace (default `ai-changelog`).

```json
{
  "category": "Fixed",
  "changelog_entry": "Resolved a failure while building release entries.",
  "summary": "Resolved an edge case in release entry construction.",
  "version": 1
}
```

Notes are stored alongside the commit object without rewriting history.
They survive `git fetch` and `git push` when you include
`refs/notes/*` in your remote configuration,
so the summaries can be shared across machines and CI runs.

The versioned JSON payload lets the rendering stage read category,
summary, and the precomputed changelog entry without contacting the model.
Existing plaintext notes remain supported and use their first summary sentence
when no stored changelog entry is available.

Each successfully completed commit is a durable checkpoint.
If processing stops before finalization,
a later run reuses stored notes and processes only commits that still need notes,
unless you explicitly use `--force`.

## 5. Semantic version tag and release grouping

Before rendering the changelog,
the tool reads all tags in the repository and filters for semantic version tags
(`vMAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCH`).

Commits are then grouped into release sections by the highest semantic version tag
that points to or precedes each commit.
Commits not yet covered by any tag fall into an `[Unreleased]` section.

### Automatic tag creation

When you pass `--create-semver-tags`,
the tool infers a release type from each commit's note category
and creates lightweight version tags automatically:

| Note category | Release type |
| ------------- | ------------ |
| `Added`       | `minor`      |
| `Changed`     | `patch`      |
| `Fixed`       | `patch`      |
| `Removed`     | `major`      |

Tags are created chronologically, starting from the highest existing tag or
`v1.0.0` if none exists.
Commits that already carry a semantic tag are skipped.

## 6. Changelog rendering

The tool builds a
[Keep a Changelog](https://keepachangelog.com/)–compliant `CHANGELOG.md`.
Finalization reads the compact Git-note payloads,
sorts commits by commit time and hash for deterministic output,
groups entries by release and category,
and writes the rendered file once.
It does not resend historical changes to the language model or re-read historical diffs.

As a result, an interrupted run can leave durable Git-note checkpoints without a new
`CHANGELOG.md`.
A later successful run completes the local grouping, merge, and file write.

Within each release section,
entries are sorted into subsections in the canonical order:
**Added → Changed → Fixed → Removed**.

If `CHANGELOG.md` already exists,
the tool performs an **incremental merge**:
it parses the existing file,
identifies release sections that are already present,
and appends only the new or missing sections.
Existing content is never overwritten.
The `[Unreleased]` section is always updated to reflect commits not yet tagged.

The final output path is configurable via `--changelog-file`
(default `CHANGELOG.md` in the repository root).
