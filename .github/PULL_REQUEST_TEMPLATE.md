## Summary

<!-- Describe what this Pull Request changes and why. -->

## Type of Change

- [ ] `feature/` — New feature or architectural capability
- [ ] `fix/` — Bug fix
- [ ] `hotfix/` — Urgent production fix
- [ ] `docs/` — Documentation or ADR update
- [ ] `refactor/` — Code refactoring without behavior change
- [ ] `test/` — Test suite additions or improvements
- [ ] `chore/` — Tooling, dependencies, or infrastructure configuration
- [ ] `ci/` — CI/CD pipeline configuration

## Stage & Scope Alignment

- [ ] Changes stay strictly within the current stage scope and avoid premature cross-stage implementation.
- [ ] Branch was created from `develop` (or `develop` -> `main` for release integration) following `<prefix>/<descriptive-kebab-case>`.
- [ ] Commits follow Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).

## Verification & Quality Checks

- [ ] Backend checks pass (`ruff check`, `ruff format --check`, `mypy`, `pytest`), if applicable.
- [ ] Frontend checks pass (`npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`), if applicable.
- [ ] Docker Compose build/healthchecks verified locally, if applicable.

## Documentation & Security

- [ ] Relevant documentation or ADRs were updated.
- [ ] No secrets, tokens, `.env` files, or credentials are included in the diff.
