# Git & Branching Workflow

The repository enforces a structured branching and commit model designed for auditability, clean code reviews, and zero direct pushes to protected integration/release branches.

---

## 1. Main Branches

| Branch | Purpose | Rule |
|---|---|---|
| `main` | Stable, verified release snapshots | Receives changes exclusively via Pull Request from `develop` (or urgent `hotfix/*`) |
| `develop` | Integration branch for completed tasks | Receives changes exclusively via Pull Request from working branches |

Direct commits to `main` and `develop` are prohibited.

---

## 2. Working Branch Naming Convention

Create every working branch from an up-to-date `develop` branch using lowercase English words separated by hyphens (`kebab-case`):

```text
<prefix>/<descriptive-short-name>
```

| Prefix | Usage | Example |
|---|---|---|
| `feature/` | New capabilities or architectural components | `feature/backend-initial-structure` |
| `fix/` | Bug fixes integrated into `develop` | `fix/healthcheck-timeout-handling` |
| `hotfix/` | Urgent production fixes | `hotfix/cors-origin-parsing` |
| `docs/` | Architecture, ADR, or developer documentation | `docs/architecture-documentation` |
| `refactor/` | Internal improvements preserving external behavior | `refactor/database-session-dependency` |
| `test/` | Additions or enhancements to automated tests | `test/readiness-degraded-cases` |
| `chore/` | Tooling, dependencies, Docker, templates, repo config | `chore/docker-configuration` |
| `ci/` | Continuous integration and delivery pipelines | `ci/github-actions-quality-gate` |

---

## 3. Conventional Commits

Every commit follows **Conventional Commits**:

```text
<type>(<optional-scope>): <imperative concise summary>
```

Common types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`.

Examples from Stage 1:
- `chore(repo): configure gitignore, gitattributes, and editorconfig`
- `feat(backend): implement modular API foundation and healthcheck endpoints`
- `feat(frontend): build enterprise SaaS layout, overview page, and live backend status`
- `docs(adr): record initial architecture decision records (ADR-001 to ADR-006)`

---

## 4. Pull Request Integration Flow

1. Pull latest `develop`: `git checkout develop && git pull origin develop`.
2. Create a scoped branch: `git checkout -b <prefix>/<name> develop`.
3. Implement in small atomic commits and run all relevant linters, type checks, and tests locally.
4. Push the branch (never force-push) and open a Pull Request targeting `develop` using `.github/PULL_REQUEST_TEMPLATE.md`.
5. Verify checks and review the diff before merging.
6. After completing a milestone stage on `develop`, open a release Pull Request from `develop` into `main`.

---

## 5. Branch Protection Configuration & Current Limitation

> **Stage 1 Environment Limitation:** During Stage 1 automated setup, the GitHub MCP server did not expose a branch-protection or ruleset configuration endpoint, and the `gh` CLI was not installed locally (`protected: false` on `main` and `develop`). In accordance with strict governance rules, branch protection was **not simulated** and must be enabled manually by the repository administrator on GitHub.

### Required Manual GitHub Settings

Repeat the following rules under **GitHub Repository -> Settings -> Branches -> Add branch protection rule** (or **Rulesets**) for both **`main`** and **`develop`**:

1. **Branch name pattern:** `main` (and a second rule for `develop`).
2. **Require a pull request before merging:** Enabled (`Require approvals: 1` when working with collaborators; `Dismiss stale pull request approvals when new commits are pushed`).
3. **Require conversation resolution before merging:** Enabled.
4. **Do not allow bypassing the above settings:** Enabled (`enforce_admins`).
5. **Restrict force pushes & deletions:** Keep **Allow force pushes** and **Allow deletions** unchecked.
6. *(Stage 8 addition)* Once CI workflows exist, enable **Require status checks to pass before merging**.

### Equivalent `gh api` Command (once `gh` CLI is installed & authenticated)

```bash
for branch in main develop; do
  gh api -X PUT "repos/VictorSilvaCamargo/enterprise-intelligence-platform/branches/${branch}/protection" \
    -H "Accept: application/vnd.github+json" \
    --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF
done
```
