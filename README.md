# AI Changelog Generator

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Super-Linter](https://github.com/electrocucaracha/ai-changelog/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)

<!-- markdown-link-check-disable-next-line -->

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![visitors](https://visitor-badge.laobi.icu/badge?page_id=electrocucaracha.ai-changelog)
[![Scc Code Badge](https://sloc.xyz/github/electrocucaracha/ai-changelog?category=code)](https://github.com/boyter/scc/)
[![Scc COCOMO Badge](https://sloc.xyz/github/electrocucaracha/ai-changelog?category=cocomo)](https://github.com/boyter/scc/)

## Overview

AI Changelog Generator automates release-note creation from Git history.
It analyzes commit diffs with an AI model,
stores per-commit summaries in Git notes,
and renders a structured CHANGELOG.md.

### What Problem Does It Solve

Writing changelogs by hand is repetitive,
easy to delay,
and often inconsistent across releases.
This project solves that by generating changelog content directly from commits,
so release notes are faster to produce and easier to keep accurate.

For quickstart, CLI options, provider configuration, and processing details,
see the GitHub Pages documentation in [docs/](docs/index.md).
