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

![Diagram](docs/assets/diagram.png)

### Reasons to Use AI Changelog Generator

Writing changelogs by hand is repetitive, time-consuming, and easy to put off. It can also lead to inconsistent formatting, missing changes, and release notes that fall out of sync with the actual development history.

AI Changelog Generator automates the process by analyzing your Git commits and turning them into structured, human-readable release notes. It keeps changelog generation close to the source of truth—your repository—making releases faster to document, more consistent, and easier to maintain.

For quickstart, CLI options, provider configuration, and processing details,
see the GitHub Pages documentation in [docs/](docs/index.md).
