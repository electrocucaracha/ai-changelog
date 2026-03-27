# Contributing to AI Changelog Generator

We welcome contributions! Here's how you can help.

## Development Setup

1. **Create a virtual environment**

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install development dependencies**

```bash
uv sync --extra test --extra eval
```

3. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

## Code Standards

- **Python version**: 3.9+
- **Style**: Black for formatting, isort for imports
- **Linting**: ruff, black, isort, pyink
- **Type checking**: mypy
- **Testing**: pytest, tox, and functional Deepeval checks with Ollama

### Before submitting changes

```bash
# Format code
make fmt

# Run linters
make lint

# Run tests
make test

# Run functional Deepeval tests
make func
```

## Deepeval Summarization Checks

The repository includes live summarization evaluation using `deepeval`
and a local `ollama` judge model. The `make func` target is the dedicated entrypoint
for these functional tests.

Behavior:

- `make test` runs the standard tox-based test suite
- `make func` installs the `test` and `eval` extras
- `make func` enables `AI_CHANGELOG_DEEPEVAL_RUN=1` for the Deepeval test run
- `make func` invokes `tests/test_deepeval_summarization.py`

Required environment for live evals:

- `AI_CHANGELOG_DEEPEVAL_RUN=1`
- `CHANGELOG_MODEL=ollama/llama3.1` or another LiteLLM-supported Ollama model
- `AI_CHANGELOG_DEEPEVAL_JUDGE_MODEL=llama3.1` or another local judge model
- optional: `AI_CHANGELOG_DEEPEVAL_BASE_URL=http://localhost:11434`
- optional: `AI_CHANGELOG_DEEPEVAL_THRESHOLD=0.5`

Make sure Ollama is running and the model exists locally:

```bash
ollama pull llama3.1
```

Examples:

```bash
# Default test run: tox-based test suite
make test

# Functional Deepeval summarization checks
CHANGELOG_MODEL=ollama/granite3.2:latest \
AI_CHANGELOG_DEEPEVAL_JUDGE_MODEL=granite3.2:latest \
make func
```

## Commit Messages

Follow conventional commit format:

```text
feat: Add new summary feature
fix: Correct git note handling
docs: Update README
refactor: Simplify config loading
test: Add tests for AI provider
```

## Pull Request Process

1. **Ensure all tests pass**

   ```bash
   uv run pytest tests/ -v
   ```

2. **Update documentation** if your changes affect functionality

3. **Include test coverage** for new features

4. **Provide clear PR description** explaining:
   - What changes you made
   - Why you made them
   - How to test the changes

## Code Review

- Be open to feedback
- Respond to review comments promptly
- Make requested changes or explain your reasoning

## Testing

Adding tests is crucial. Here's the structure:

```python
# tests/test_my_feature.py
import pytest
from my_module import my_function

def test_my_function():
    result = my_function("test")
    assert result == "expected"
```

## Documentation

- Update docstrings for changed functions
- Update CONTRIBUTING if development or testing workflow changes
- Add examples for new features

## Reporting Issues

Use GitHub issues with:

1. **Clear title** describing the problem
2. **Description** with:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Python version and OS
3. **Error logs** if applicable

## Getting Help

- Ask questions in GitHub discussions
- Check existing issues for similar problems
- Review documentation in README and this guide
