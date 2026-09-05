# Proposal: Repository Quality Gates

## Intent

The pipeline has real quality gaps. CI validates data and runs pytest but never
regenerates `output/`, so committed `output/` can silently drift from `data/`.
There is zero lint, format, type-check, or coverage safety net (`pyproject.toml`
carries only pytest config). URLs in `projects.json` (some empty) and
`social.json` are never checked. This change installs standard, low-friction
quality gates so regressions fail loudly in CI and locally.

## Scope

### In Scope
- **Output-freshness gate**: CI runs `python -m generators.generate_all` then
  `git diff --exit-code -- output/`; fails on drift.
- **Ruff**: lint + format config in `pyproject.toml`; CI `ruff check` +
  `ruff format --check`; fix existing violations for a clean baseline.
- **mypy**: config + CI type-check of `generators/`; pragmatic strictness.
- **Coverage**: `pytest-cov`; CI coverage with threshold set at/below measured current.
- **Pre-commit hooks**: `.pre-commit-config.yaml` (ruff format+check + fast
  validate/pytest subset); `pre-commit` dev dep; document `pre-commit install`.
- **Link validation**: `generators/links.py` validating `projects.json` /
  `social.json` URLs; warn-only, non-fatal, offline-safe, `SKIP_LINK_CHECK=1`,
  mirroring `generators/icons.py`.

### Out of Scope
- Visual level-up of LinkedIn/CV/portfolio (separate `visual-polish-profiles`).
- CLI ergonomics / Makefile (deferred).
- Monorepo restructure; deploy automation; local icon SVG mirroring.

## Capabilities

### New Capabilities
- None (extends existing tooling/validation capabilities).

### Modified Capabilities
- `generator-tooling`: add output-freshness CI gate, ruff, mypy, coverage, and pre-commit hook requirements.
- `generator-validation`: add URL link-validation (warn-only, skippable) alongside schema validation.

## Approach

Add dev tooling as `[project.optional-dependencies] dev` (ruff, mypy,
pytest-cov, pre-commit) — runtime deps stay minimal. Config lives in
`pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, coverage). CI gains discrete
steps; network-dependent checks run with skip flags. Link check reuses the
proven stdlib `urllib` warn-only pattern from `icons.py`. Fix existing lint/type
findings mechanically with no behavior change under strict TDD.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | ruff/mypy/coverage config; dev deps |
| `.github/workflows/validate.yml` | Modified | freshness, ruff, mypy, coverage steps |
| `.pre-commit-config.yaml` | New | local hooks |
| `generators/links.py` | New | warn-only URL checker |
| `tests/` | New | link checker tests (offline) |
| `generators/*.py` | Modified | lint/type fixes, no behavior change |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Network flakiness for link/icon checks in CI | Med | Warn-only + `SKIP_LINK_CHECK=1`/`SKIP_ICON_CHECK=1` in CI |
| Ruff/mypy fixes alter behavior | Low | Mechanical only; full pytest under strict TDD |
| Coverage threshold too aggressive | Low | Measure current first; set at/below |
| Dev deps leak into runtime | Low | Keep in `[dev]` extra only |

## Rollback Plan

Revert the change commit(s). Each gate is independent — a single failing gate
can be temporarily disabled by removing its CI step / hook without touching data
or generator behavior. `generators/links.py` is additive and warn-only.

## Dependencies

- Dev-only: `ruff`, `mypy`, `pytest-cov`, `pre-commit`.

## Success Criteria

- [ ] CI fails when committed `output/` drifts from freshly generated output.
- [ ] `ruff check`, `ruff format --check`, and mypy pass clean in CI.
- [ ] Coverage runs in CI at a realistic threshold; 113 tests still pass.
- [ ] `pre-commit install` documented and hooks run locally.
- [ ] Link checker warns on empty/unreachable URLs, never fails, skippable offline.
