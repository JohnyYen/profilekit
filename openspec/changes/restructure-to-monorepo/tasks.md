# Tasks: Restructure to Source Monorepo

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 600–900 (CI YAMLs + subtree history grafts + test/check scripts) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (CI path-scoping) → PR 2 (portfolio subtree import) → PR 3 (cv subtree import + verification) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Path-scoped CI workflows | PR 1 | `gh act pull_request --job validate` (dry) or manual review of YAML path filters | N/A — declarative YAML; validated by spec scenario assertions in the CI job itself | Revert `.github/workflows/validate.yml` edits; delete `.github/workflows/portfolio.yml` |
| 2 | Portfolio subtree import | PR 2 | `pnpm install --frozen-lockfile && pnpm build` inside `apps/portfolio/` | `pnpm build` must exit 0 with no cross-repo fetch | `git revert` the subtree-add commit; directory is self-contained |
| 3 | CV subtree import + full verification | PR 3 | `uv run pytest -q` (113 tests green) + layout/output contract checks | `uv run pytest -q` exits 0; `output/` lists 5 artifacts | `git revert` the cv subtree-add commit; Python suite untouched |

---

## Phase 1: CI Path-Scoping (spec Req 5)

> Delivers PR 1. No network access to external repos required.

- [ ] 1.1 **[RED]** Write `tests/test_ci_path_filters.py`: assert `.github/workflows/validate.yml` contains `paths:` entries covering `data/**`, `generators/**`, `schemas/**`, `tests/**`, and `cv/**`; assert it does NOT contain `apps/portfolio/**` in any `paths:` block.
- [ ] 1.2 **[RED]** Extend `tests/test_ci_path_filters.py`: assert `.github/workflows/portfolio.yml` exists and contains `paths:` entry `apps/portfolio/**`; assert it does NOT contain `data/**`, `generators/**`, `schemas/**`, `tests/**`, or `cv/**` in any `paths:` block.
- [ ] 1.3 **[GREEN]** Update `.github/workflows/validate.yml`: replace the `pip install -e ".[dev]"` install step with `uv sync`; add `on.pull_request.paths` filter (`data/**`, `generators/**`, `schemas/**`, `tests/**`, `cv/**`); change the pytest run step to `uv run pytest -q`; change the validate step to `uv run python generators/validate.py`.
- [ ] 1.4 **[GREEN]** Create `.github/workflows/portfolio.yml`: `on.pull_request.paths: ['apps/portfolio/**']`; steps: `actions/checkout@v4`, `pnpm/action-setup` (latest), `actions/setup-node@v4` (pinned LTS), `pnpm install --frozen-lockfile` (working-directory: `apps/portfolio`), `pnpm build` (working-directory: `apps/portfolio`).
- [ ] 1.5 Run `uv run pytest -q` — verify `test_ci_path_filters` passes; confirm existing 113 tests remain green.

---

## Phase 2: Portfolio Subtree Import (spec Req 3)

> Delivers PR 2. **Requires network access** to `https://github.com/JohnyYen/my-portfolio-terminal`. These git commands must be run interactively by the user (they hit the remote).

- [ ] 2.1 **[RED]** Write `tests/test_monorepo_layout.py`: assert `apps/portfolio/` exists as a directory in the repo root; assert `apps/portfolio/package.json` is present; assert `apps/portfolio/pnpm-lock.yaml` is present; assert no `.gitmodules` entry references `my-portfolio-terminal` or `portfolio` (spec Req 3 submodule-check scenario).
- [ ] 2.2 **[RED]** Extend `tests/test_monorepo_layout.py`: assert `apps/portfolio/app/data/` exists and is non-empty (portfolio data source unchanged scenario, spec Req 2).
- [ ] 2.3 **[GREEN — user-interactive]** Add git remote and run subtree add (network required):
  ```
  git remote add portfolio-src https://github.com/JohnyYen/my-portfolio-terminal
  git subtree add --prefix=apps/portfolio portfolio-src main
  ```
- [ ] 2.4 **[GREEN]** Verify `apps/portfolio/` is present, contains `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and `app/data/` with TypeScript modules; confirm no `.gitmodules` entry for the portfolio.
- [ ] 2.5 **[GREEN]** Inside `apps/portfolio/`, run `pnpm install --frozen-lockfile && pnpm build` — build must exit 0 with no cross-repo fetch (spec Req 3 portfolio-builds scenario).
- [ ] 2.6 Run `uv run pytest -q` — verify `test_monorepo_layout` (layout assertions) passes; confirm 113 existing tests still green.

---

## Phase 3: CV Subtree Import (spec Req 4)

> Delivers start of PR 3. **Requires network access** to `https://github.com/JohnyYen/my-cv`. Run git commands interactively.

- [ ] 3.1 **[RED]** Extend `tests/test_monorepo_layout.py`: assert `cv/` exists in the repo root; assert it contains at least one file (RenderCV config present); assert no hand-maintained profile-data JSON exists under `cv/` (spec Req 4 no-divergent-copy scenario).
- [ ] 3.2 **[GREEN — user-interactive]** Add git remote and run subtree add (network required):
  ```
  git remote add cv-src https://github.com/JohnyYen/my-cv
  git subtree add --prefix=cv cv-src main
  ```
- [ ] 3.3 **[GREEN]** Confirm `cv/` is present and contains the RenderCV configuration; confirm no hand-authored profile JSON exists under `cv/` (data is derived from `output/cv.yml`).

---

## Phase 4: Final Verification (spec Reqs 1, 2, 6, 7, 8)

> Completes PR 3. All verification tasks are local.

- [ ] 4.1 **[RED]** Extend `tests/test_monorepo_layout.py`: assert all seven canonical top-level directories exist — `data/`, `schemas/`, `generators/`, `output/`, `apps/portfolio/`, `cv/`, `tests/` (spec Req 1 layout scenario).
- [ ] 4.2 **[RED]** Write `tests/test_output_contract.py`: assert `output/` contains exactly these five files — `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml` — after running all generators (spec Req 7 output-artifacts scenario).
- [ ] 4.3 **[RED]** Extend `tests/test_monorepo_layout.py`: assert no directory named `JohnyYen` exists at the repo root (spec Req 6 external-targets scenario).
- [ ] 4.4 **[GREEN]** Run all generators (`uv run python generators/generate_github_readme.py`, etc.) and confirm `output/` contains the five expected artifacts with names matching the established contract.
- [ ] 4.5 Run full suite: `uv run pytest -q` — all tests (including new layout, CI-filter, and output-contract tests) must exit 0; confirm original 113 tests remain green (spec Req 8).
- [ ] 4.6 Spot-check no divergent pipeline-consumer data: confirm no authored JSON outside `data/`, `output/`, and `apps/portfolio/app/data/` (the known deferred carve-out) duplicates profile fields (spec Req 2 no-duplicate-data scenario).
