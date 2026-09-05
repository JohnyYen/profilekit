# Tasks: Repository Quality Gates

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–600 (ruff/mypy mechanical fixes inflate count significantly) |
| 400-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | Single PR — `size:exception` (maintainer pre-approved) |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Single `size:exception` PR — all six gates | PR 1 | `.venv/bin/python -m pytest -q` | `python generators/validate.py` with `SKIP_LINK_CHECK=1 SKIP_ICON_CHECK=1` | Revert commit; each gate independently removable from CI without touching data/generators |

---

## Phase 1: Dev Dependencies and Config Foundation

- [x] 1.1 Edit `pyproject.toml` `[project.optional-dependencies] dev` to add `ruff>=0.4`, `mypy>=1.10`, `pytest-cov>=5`, `pre-commit>=3`; keep `jsonschema>=4` as runtime dep only.
- [x] 1.2 Add `[tool.ruff]` section to `pyproject.toml`: `target-version = "py311"`, `line-length = 100`, `select = ["E","F","I","UP","B","SIM"]`; `src = ["generators","tests"]`.
- [x] 1.3 Add `[tool.mypy]` section to `pyproject.toml`: `python_version = "3.11"`, `ignore_missing_imports = true`, `files = ["generators/"]`; no strict mode.
- [x] 1.4 Add `[tool.pytest.ini_options]` `addopts` entry `--cov=generators --cov-report=term-missing` (leave `--cov-fail-under` placeholder `0` until task 3.1 fills the measured value).
- [x] 1.5 Install updated dependencies into `.venv`: run `pip install -e ".[dev]"` inside the venv; verify `ruff --version`, `mypy --version`, `pytest-cov --version`.
- [x] 1.6 Update `openspec/config.yaml` `apply.test_command` and `verify.test_command` from `uv run pytest -q` to `.venv/bin/python -m pytest -q`.

## Phase 2: Ruff Baseline (mechanical, no behavior change)

- [x] 2.1 Run `ruff format generators/ tests/` to auto-format all Python source files; verify `git diff` shows only whitespace/style changes.
- [x] 2.2 Run `ruff check --fix generators/ tests/` to auto-fix safe violations; review remaining unfixed violations.
- [x] 2.3 Manually resolve any remaining `ruff check` violations that `--fix` cannot handle; confirm `ruff check generators/ tests/` exits zero.
- [x] 2.4 Run `.venv/bin/python -m pytest -q` (no cov yet); MUST still see 113 tests pass and zero failures.

## Phase 3: mypy Baseline (mechanical, no behavior change)

- [x] 3.1 Run `mypy generators/` and catalogue all reported errors; add minimal annotations (`# type: ignore` only where the type is genuinely unknowable from context; prefer real type hints).
- [x] 3.2 Resolve mypy errors in `generators/validate.py`, `generators/icons.py`, `generators/utils.py`, `generators/render.py` with minimal annotations; do not alter behavior.
- [x] 3.3 Resolve mypy errors in generator scripts (`generate_github_readme.py`, `generate_linkedin.py`, `generate_cv.py`, `generate_portfolio.py`, `generate_all.py`); do not alter behavior.
- [x] 3.4 Confirm `mypy generators/` exits zero; run pytest again to confirm 113 tests still pass.

## Phase 4: Coverage Baseline Measurement

- [x] 4.1 Run `.venv/bin/python -m pytest -q --cov=generators --cov-report=term-missing` (without `--cov-fail-under`) and record the measured total coverage percentage.
- [x] 4.2 Set `--cov-fail-under=<measured_value>` in `pyproject.toml` `addopts` (use the exact measured integer or one point below to guard against floating-point fluctuation). Record this number in a comment.
- [x] 4.3 Run `.venv/bin/python -m pytest -q` with the threshold in place; confirm all 113 tests pass and coverage gate passes (exit 0).

## Phase 5: Link Validation — RED tests first (TDD)

- [x] 5.1 **RED** — Create `tests/test_links.py` with failing tests for `generators/links.py` (module does not exist yet):
  - `test_check_links_offline_returns_empty` — `offline=True` returns `[]`, no urlopen call (mirrors `test_check_icons_offline_returns_empty`).
  - `test_check_links_skip_env_var` — `SKIP_LINK_CHECK=1` env var returns `[]`, no urlopen call.
  - `test_check_links_200_ok_no_warnings` — mocked 200 response → empty warning list.
  - `test_check_links_non_200_produces_warning` — mocked 404 response → warning list with URL context.
  - `test_check_links_url_error_produces_warning_no_exception` — `URLError` → warning, no raise.
  - `test_check_links_empty_url_skipped` — projects entry with `"url": ""` is skipped (empty URL is not reported as broken).
  - `test_check_links_social_key_checked` — social dict with a valid http URL is checked (mocked 200 → no warning).
  - Run `.venv/bin/python -m pytest tests/test_links.py -q`; MUST see 7 failures (`ImportError` / module not found).

- [x] 5.2 **GREEN** — Create `generators/links.py` mirroring `generators/icons.py`:
  - Module docstring matches icons.py style.
  - `check_links(projects: list, social: dict, *, offline: bool = False, timeout: int = 5) -> list[str]` signature.
  - Respects `SKIP_LINK_CHECK=1` env var and `offline` kwarg → returns `[]` immediately.
  - `_resolve_project_urls(projects)` extracts `(name, url)` for entries where `url` is a non-empty string starting with `http`.
  - `_resolve_social_urls(social)` extracts `(key, value)` for values that are non-empty strings starting with `http`.
  - `_check_url(label, url, timeout)` mirrors icons.py: HEAD request, GET fallback on 405, returns warning string or `None`, never raises.
  - Run `.venv/bin/python -m pytest tests/test_links.py -q`; all 7 tests MUST pass.

- [x] 5.3 **REFACTOR** — Review `generators/links.py` for duplication with `icons.py`; extract shared `_check_url` helper only if both modules would benefit and tests still pass; keep the change mechanical.
  - Run `.venv/bin/python -m pytest -q`; MUST see 120 tests pass (113 + 7 new).

## Phase 6: Wire Link Check into validate.py

- [x] 6.1 In `generators/validate.py` `main()`, add a link-validation block after the existing icons block; guard with `try/except ImportError` mirroring the icons pattern; pass `projects_data` and `social_data`; print each warning as `WARNING (link): <msg>` to stderr.
- [x] 6.2 Load `social.json` in `validate.py` (currently only `about.json` and `projects.json` are loaded at the cross-file check level); add `social_path` / `social_data` load before the link check call.
- [x] 6.3 Run `.venv/bin/python -m pytest -q`; MUST see 120 tests pass and zero regressions.
- [x] 6.4 Run `python generators/validate.py` with `SKIP_LINK_CHECK=1 SKIP_ICON_CHECK=1`; MUST exit 0.

## Phase 7: Pre-commit Configuration

- [x] 7.1 Create `.pre-commit-config.yaml` with:
  - `repos` entry for `https://github.com/astral-sh/ruff-pre-commit` (pinned to a recent tag); hooks: `ruff` (args: `--fix`) and `ruff-format`.
  - Local repo hook `validate-fast`: `language: system`, `entry: python generators/validate.py`, `pass_filenames: false`, env: `SKIP_ICON_CHECK=1 SKIP_LINK_CHECK=1`; `types: [json]`.
- [x] 7.2 Confirm `pre-commit run --all-files` passes on the current clean working tree (requires `pre-commit` installed in `.venv`).

## Phase 8: CI Workflow Update

- [x] 8.1 Edit `.github/workflows/validate.yml` — update `Install dependencies` step from `pip install -e ".[dev]"` (already correct) to keep as-is; no change needed here.
- [x] 8.2 Add CI step `Ruff lint` after install: `run: ruff check generators/ tests/`.
- [x] 8.3 Add CI step `Ruff format check`: `run: ruff format --check generators/ tests/`.
- [x] 8.4 Add CI step `mypy`: `run: mypy generators/`.
- [x] 8.5 Edit existing `Run pytest` step: replace `python -m pytest -q` with `python -m pytest -q` (already uses `--cov` via `addopts`; add explicit `--cov-fail-under=<value>` if addopts is not picked up in CI). Add `SKIP_LINK_CHECK: "1"` alongside existing `SKIP_ICON_CHECK: "1"`.
- [x] 8.6 Add CI step `Freshness gate` (last step): `python -m generators.generate_all` then `git diff --exit-code -- output/`; set `SKIP_ICON_CHECK: "1"` and `SKIP_LINK_CHECK: "1"` on this step.
- [x] 8.7 Verify the step order in `validate.yml` matches the specified sequence: install → ruff check → ruff format check → mypy → pytest (with cov) → validate → freshness.

## Phase 9: Final Verification

- [x] 9.1 Run `.venv/bin/python -m pytest -q` from repo root; MUST see exactly 120 tests pass (113 original + 7 link tests), zero failures, coverage gate green.
- [x] 9.2 Run `ruff check generators/ tests/` and `ruff format --check generators/ tests/`; both MUST exit 0.
- [x] 9.3 Run `mypy generators/`; MUST exit 0 with zero errors.
- [x] 9.4 Confirm `output/` is up-to-date: run `python -m generators.generate_all` with `SKIP_ICON_CHECK=1 SKIP_LINK_CHECK=1`, then `git diff -- output/`; MUST show no diff.
- [x] 9.5 Confirm carry-forward invariant: `git diff -- README.md` MUST be empty (root README untouched).
- [x] 9.6 Confirm `generators/` write-only-to-`output/` invariant: no generator writes outside `output/` directory.
