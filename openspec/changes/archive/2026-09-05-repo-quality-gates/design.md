# Design: Repository Quality Gates

## Technical Approach

Add six independent, low-friction gates over the existing data-driven pipeline
without touching generator behavior. Config centralizes in `pyproject.toml`
(`[tool.ruff]`, `[tool.mypy]`, coverage addopts); CI gains discrete steps in
`validate.yml`; a new `generators/links.py` mirrors the proven warn-only
`generators/icons.py` pattern exactly. Existing lint/type findings are fixed
mechanically. Standardize the runner on `.venv/bin/python -m pytest -q` locally
and `pip install -e ".[dev]"` + `python -m pytest -q` in CI.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Output freshness | CI: `python -m generators.generate_all` then `git diff --exit-code -- output/` | Hash manifest; drop tracking `output/` | Zero new code; `output/` is tracked deploy source |
| Lint/format | Ruff (`check` + `format --check`) | black+flake8+isort | One fast tool, config in pyproject |
| Types | mypy, pragmatic (`generators/` only, `ignore_missing_imports`) | Strict all-modules; pyright | Untyped deps (jsonschema); avoid churn |
| Coverage | pytest-cov addopts + `--cov-fail-under` set at/below measured | CI-only flag | Same threshold local+CI; measure first |
| Link check | stdlib `urllib`, warn-only, `SKIP_LINK_CHECK=1` | requests dep; fail-on-broken | Mirrors icons.py; offline-safe CI |
| Dev deps | `[project.optional-dependencies] dev` | separate requirements-dev.txt | Extends existing `dev` extra |
| Runner | `.venv/bin/python -m pytest -q` local | `uv run pytest` (config.yaml) | uv not in use; venv is working runner |

## Data Flow

    data/projects.json, social.json ──→ links.check_links() ──→ [warnings] ──→ stderr
                                              │ (SKIP_LINK_CHECK / offline → [])
    validate.py ──→ schema + icons + links warnings (non-fatal)

    CI: generate_all ──→ output/ ──→ git diff --exit-code (FAILS on drift)

## File Changes

| File | Action | Description |
|---|---|---|
| `pyproject.toml` | Modify | `[tool.ruff]` (line-length 100, target-version py311, rules E,F,I,UP,B,SIM), `[tool.mypy]`, coverage addopts; `dev` extra += ruff, mypy, pytest-cov, pre-commit |
| `.github/workflows/validate.yml` | Modify | Add ruff check + format-check, mypy, coverage run, freshness gate; set `SKIP_LINK_CHECK: "1"` alongside `SKIP_ICON_CHECK` |
| `.pre-commit-config.yaml` | Create | ruff + ruff-format hooks; local validate + fast pytest hook |
| `generators/links.py` | Create | warn-only URL checker (mirrors icons.py) |
| `tests/test_links.py` | Create | offline/skip/200/non-200/URLError + empty-URL tests |
| `generators/validate.py` | Modify | invoke `check_links` (guarded ImportError, like icons) |
| `generators/*.py`, `tests/*.py` | Modify | mechanical ruff/mypy fixes, no behavior change |
| `openspec/config.yaml` | Modify | `test_command` → `.venv/bin/python -m pytest -q` |

## Interfaces / Contracts

`generators/links.py` mirrors `icons.py` signatures:

```python
def check_links(projects: list, social: dict, *, offline: bool = False,
                timeout: int = 5) -> list[str]:
    # offline or SKIP_LINK_CHECK=1 → []
    # projects: skip empty/missing "url" (empty string is not broken → skip)
    # social: check github/linkedin/cvUrl values that are http(s) URLs
    # HEAD, GET fallback on 405; never raises; warning: "Link not reachable (...)"
```

CI order (append after existing steps): install → ruff check → ruff format
--check → mypy `generators/` → pytest (with cov) → validate → **freshness**
(`generate_all` + `git diff --exit-code -- output/`). Freshness last so lint/type
failures surface first and generation runs on a clean tree.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `check_links`: offline, `SKIP_LINK_CHECK`, 200, non-200, URLError, empty-string URL skipped, social keys | mock `urllib.request.urlopen`, mirror test_icons.py |
| Integration | validate.py still exits 0 with links guarded | existing validate tests unchanged |
| CI gate | freshness fails on drift | inherent to `git diff --exit-code` |

Baseline steps (executor, not design): run `ruff format`/`ruff check --fix`
mechanically; run mypy and add minimal annotations (avoid over-tightening —
prefer `ignore_missing_imports` for jsonschema, precise dict param types on
existing helpers); run `pytest --cov=generators --cov-report=term-missing` to
measure, then set `--cov-fail-under` at/below that number.

## Threat Matrix

Applicable — the design adds CI shell steps and network I/O.

| Row | Status | Safe behavior / test |
|---|---|---|
| Shell command injection | N/A | No user input in shell; `links.py` uses `urllib`, no `subprocess`/shell |
| Subprocess/process integration | Applicable | CI `git diff --exit-code` is static; freshness fails closed on drift |
| Network I/O failure | Applicable | Warn-only + `SKIP_LINK_CHECK=1` in CI; URLError → warning, never raises (RED test) |
| VCS/PR automation | N/A | No PR/branch automation added |
| Executable-file classification | N/A | No file-type routing |

## Migration / Rollout

No data migration. Gates are independent; any single failing gate can be
disabled by removing its CI step/hook without touching data or generators.
Set `--cov-fail-under` conservatively on first pass.

## Open Questions

- [ ] Exact `--cov-fail-under` value — resolved during baseline measurement, not design-blocking.
