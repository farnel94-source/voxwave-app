# Contributing to VoxWave

Thank you for your interest in VoxWave! This document explains how to contribute.

## The golden rule

**Open an issue first, code second.** Every contribution — bug fix, feature, refactor — starts with a discussion. PRs without a linked, approved issue will be closed.

## What we accept

### Always welcome
- **Bug reports** — found a crash, wrong behavior, or edge case? Open an issue
- **Bug fixes** — fix a confirmed bug with a PR linked to the issue
- **Translations** — add or improve interface translations (currently 15 languages)
- **Documentation** — improve the README, guides, or code comments
- **Tests** — increase test coverage or fix flaky tests

### Needs approval first
- **New features** — open an issue describing the feature and wait for approval before coding
- **Refactoring** — discuss the scope in an issue first
- **Architecture changes** — must be approved by the maintainer

### Will be declined
- PRs that bypass or weaken the licensing system
- PRs without a linked issue
- Large refactors submitted without prior discussion

## How decisions are made

VoxWave is maintained by a single developer. All roadmap, architecture, and feature decisions are made by the maintainer. Community input is valued and encouraged through issues and discussions, but the maintainer has final say.

## The code is yours

VoxWave is 100% open source (MIT). The entire codebase — including cloud integrations (Groq, OpenAI) — is public. You can fork it, modify it, run it with your own API keys, and use it however you want. The paid plan is a convenience service, not a code restriction.

## Development setup

```bash
git clone https://github.com/farnel94-source/voxwave-app.git
cd voxwave-app
python -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Run the app
```bash
python -m voxwave
```

### Run tests
```bash
pytest tests/ -v
```

### Code style
- Python: `black` for formatting, `flake8` for linting
- Variables/functions: `snake_case`
- Files: `kebab-case`
- 4 spaces indentation

## Submitting a PR

1. Fork the repo
2. Create a branch: `feat/my-feature` or `fix/my-bug`
3. Write tests for your changes
4. Make sure all tests pass: `pytest tests/ -v`
5. Format your code: `black src/ tests/`
6. Submit the PR referencing the issue number

## Reporting bugs

Use the [Bug Report template](https://github.com/farnel94-source/voxwave-app/issues/new?template=bug_report.yml) and include:
- OS and version (Windows 10/11, Linux distro)
- Steps to reproduce
- Expected vs actual behavior
- Logs if available (`~/.voxwave/voxwave.log`)

## Code of Conduct

Be respectful. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
