# Contributing to CDDBS

Thank you for your interest in contributing to the Counter-Disinformation Database System.

## Getting Started

1. Fork the repository
2. Clone your fork and set up the development environment:
   ```bash
   git clone https://github.com/<your-username>/cddbs-prod.git
   cd cddbs-prod
   git remote add upstream https://github.com/Be11aMer/cddbs-prod.git
   ```
3. Switch to the `development` branch — **all work starts here**:
   ```bash
   git checkout development
   ```
4. Install git hooks:
   ```bash
   bash scripts/install-hooks.sh
   ```
5. Set up your environment (see [DEVELOPER.md](DEVELOPER.md) for full details):
   ```bash
   cp .env.example .env   # add your API keys
   docker-compose up --build
   ```

## Branching Rules

This project enforces a strict branching policy:

- **`main`** is production-only. Do not branch from or target `main`.
- **`development`** is the active integration branch.
- **All feature/bugfix branches must be created from `development`.**
- **All PRs must target `development`.**

```bash
git checkout development
git pull upstream development
git checkout -b feature/my-feature
# ... work ...
git push -u origin feature/my-feature
# Open PR targeting 'development' on the upstream repo
```

## Before Submitting a PR

1. **Run linting:**
   ```bash
   ruff check src/ tests/
   ```
2. **Run tests:**
   ```bash
   pytest tests/ -v
   ```
3. **Check documentation drift:**
   ```bash
   python scripts/check_docs_drift.py
   ```
4. **Update documentation** — if you add/change endpoints, models, or components, update `DEVELOPER.md`.

All of these checks run in CI and must pass before merging.

## Code Style

- Python: enforced by [ruff](https://docs.astral.sh/ruff/) (config in `ruff.toml`)
- TypeScript/React: standard practices, MUI components
- Keep changes focused — one feature or fix per PR
- Write descriptive commit messages

## What to Contribute

- Bug fixes
- Test coverage improvements
- Documentation improvements
- New collectors (see `src/cddbs/collectors/`)
- New disinformation narratives (see `src/cddbs/data/known_narratives.json`)
- Frontend improvements

## Security

- **Never commit API keys, tokens, passwords, or credentials**
- Use environment variables for all secrets
- CI will automatically scan PRs for leaked credentials and reject them
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

## Pull Request Process

1. Ensure all CI checks pass
2. Provide a clear description of what changed and why
3. Link related issues if applicable
4. A code owner will review your PR

## Code of Conduct

Be respectful, constructive, and collaborative. We're building tools to counter disinformation — let's lead by example with honest, transparent communication.
