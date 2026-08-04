---
description: "Markdown writing standards for this project: use semantic line breaks for prose, preserve readable source formatting, and keep Markdown structure consistent."
applyTo: "**/*.md"
---

# Markdown Writing Guidelines

Use Semantic Line Breaks (SemBr) for Markdown prose in this repository.
Write source text so each line represents a meaningful unit of thought,
while preserving identical rendered output.

## Core Rules

- Add line breaks at semantic boundaries rather than wrapping at arbitrary widths.
- Always break after a sentence ending with `.`, `!`, or `?`.
- Usually break after an independent clause ending with `,`, `;`, or `:` when it improves readability.
- Optionally break after a dependent clause when it clarifies meaning or keeps prose manageable.
- Do not insert line breaks that change rendered output or meaning.
- Do not split inside a hyphenated word.

## Markdown Structure

- Keep headings short, descriptive, and consistently capitalized with the surrounding document style.
- Leave a blank line before and after headings, lists, block quotes, and fenced code blocks.
- Keep one list item per line unless a wrapped continuation is needed for clarity.
- Prefer ordered and unordered lists when they make content easier to scan than dense paragraphs.
- Preserve existing Markdown features such as tables, code fences, link syntax, and callouts.

## Line Length Guidance

- Prefer lines at or under 80 characters when practical.
- Allow longer lines when needed for URLs, Markdown links, inline code, or other markup that would become harder to read if split.
- Break prose semantically, not purely to satisfy a column limit.

## Editing Behavior

- Apply semantic line breaks to new or materially revised prose.
- Do not reflow untouched paragraphs only for style consistency.
- Preserve intentional hard line breaks and Markdown constructs where line structure affects rendering.
- Keep surrounding formatting stable when editing a small section of a larger document.

## Links And Inline Elements

- Keep links readable; break before or after a hyperlink when needed, not in a way that obscures the sentence.
- Keep inline code concise and use it for commands, paths, environment variables, and identifiers.
- Avoid trailing spaces for formatting unless a hard Markdown line break is explicitly intended.

## Example

```md
## Overview

AI Changelog Generator automates release-note creation from Git history.
It analyzes commit diffs with an AI model,
stores per-commit summaries in Git notes,
and renders a structured CHANGELOG.md.
```
