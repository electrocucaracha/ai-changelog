# How It Works

AI Changelog Generator uses Git history plus an AI model to produce release-ready changelog content.

## 1. Repository scanning

The tool walks commit history in the target repository.
You can process the full history or limit to the most recent commits.

## 2. Diff analysis

For each commit,
it extracts changed files and diff content.

## 3. Summary generation

The configured model generates concise summaries from each commit diff.

## 4. Git notes storage

Each summary is written to Git notes in a dedicated namespace.
This preserves commit history while attaching metadata to commits.

## 5. Tag and release grouping

The tool reads semantic version tags to group commits into release sections.
If needed,
it can create semantic version tags from note categories.

## 6. Changelog rendering

The final output is written to CHANGELOG.md.
If the changelog already exists,
missing release sections are appended instead of replacing the full file.
