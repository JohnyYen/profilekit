# Apply Progress: repo-quality-gates

**Mode**: Strict TDD. Applied inline by the orchestrator (the delegated apply was
interrupted twice by the user, who asked to continue directly).

## Status: DONE — all 7 phases complete, all gates green.

## Final verification (all passing)
| Gate | Command | Result |
|------|---------|--------|
| Lint | `ruff check .` | All checks passed |
| Format | `ruff format --check .` | 33 files already formatted |
| Types | `mypy generators/` | Success: no issues (11 files) |
| Tests + coverage | `python -m pytest -q` | 120 passed; coverage 81.67% ≥ 80% |
| Data validation | `python generators/validate.py` | All validations passed |
| Output freshness | `generate_all` + `git diff -- output/` | output/ up to date |
| README guard | `git diff README.md` | clean (untouched) |

## What was implemented
1. **Dev deps**: `pyproject.toml` `[project.optional-dependencies] dev` (ruff, mypy, pytest-cov, pre-commit). Added `[build-system]` (setuptools) and `[tool.setuptools] py-modules = []` so `pip install -e ".[dev]"` works despite the flat multi-dir layout.
2. **Ruff**: `[tool.ruff]` (py311, line-length 100, rules E/F/I/UP/B/SIM). Formatted + fixed all violations. Per-file-ignores: `E402` for `generate_all.py` (intentional sys.path bootstrap), `E501` for `tests/*` docstrings. `extend-exclude` for apps/, cv/, openspec/, output/, data/, schemas/, assets/.
3. **mypy**: `[tool.mypy]` (py311, ignore_missing_imports, files=generators/). Added `generators/__init__.py` (fixes "found twice"). Fixed annotations: `load_json`/`validate._load_json` → `Any`; `skill_icon` → `tuple[...] | None` (annotation matched actual behavior; the `is None` caller contract was preserved — no behavior change).
4. **Coverage**: `pytest-cov` via addopts `--cov=generators --cov-fail-under=80` (baseline measured at 82%, threshold set below at 80). `openspec/config.yaml coverage_threshold` → 80.
5. **Link validation**: new `generators/links.py` (stdlib urllib, HEAD+GET-fallback, warns on empty/unreachable, non-fatal, skippable `SKIP_LINK_CHECK=1`), mirroring `icons.py`. 7 TDD tests in `tests/test_links.py` (RED confirmed before impl). Wired non-fatally into `validate.py`.
6. **Pre-commit**: `.pre-commit-config.yaml` (ruff + ruff-format official hooks; local mypy, validate, pytest hooks; network checks skipped for fast offline commits). Documented `pre-commit install`.
7. **CI**: `.github/workflows/validate.yml` rewritten pip-based (was uv): setup-python 3.11, `pip install -e ".[dev]"`, steps for ruff check, ruff format --check, mypy, pytest+coverage, validate, and **output-freshness gate** (`generate_all` + `git diff --exit-code -- output/`). `SKIP_ICON_CHECK`/`SKIP_LINK_CHECK` set at job level. `config.yaml test_command` reconciled to `.venv/bin/python -m pytest -q`; removed spurious `uv.lock`.

## Deviations from tasks
- CI standardized on **pip** (not uv) per the design's runner reconciliation; removed the `uv.lock` a prior run left behind.
- Added `generators/__init__.py`, `[build-system]`, `py-modules=[]`, and ruff `extend-exclude` — not spelled out in tasks but required for the editable install + mypy resolution to work given the flat layout and newly-present `apps/`/`cv/` directories.

## Context note
`apps/portfolio/` (Next.js) and `cv/` (RenderCV) are now tracked in the repo (added outside this change). They are OUT OF SCOPE for these Python quality gates and are explicitly excluded from ruff/mypy/pytest.
