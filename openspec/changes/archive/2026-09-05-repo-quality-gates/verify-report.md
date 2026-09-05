# Verify Report: repo-quality-gates

**Verdict: PASS** — all specified quality gates implemented and green. Verified by
running each gate directly.

## Evidence
| # | Requirement | Command | Result |
|---|-------------|---------|--------|
| 1 | Lint (ruff) | `ruff check .` | All checks passed |
| 2 | Format (ruff) | `ruff format --check .` | 33 files already formatted |
| 3 | Type check (mypy) | `mypy generators/` | Success: no issues (11 files) |
| 4 | Coverage threshold | `pytest -q` | 120 passed; coverage 81.67% ≥ 80% (`--cov-fail-under=80` enforced) |
| 5 | Schema validation | `python generators/validate.py` | All validations passed |
| 6 | Link validation | `tests/test_links.py` | 7/7 pass; non-fatal, skippable `SKIP_LINK_CHECK=1`; wired into validate.py |
| 7 | Output freshness gate | `generate_all` + `git diff --exit-code -- output/` | output/ up to date (no drift) |
| 8 | Pre-commit hooks | `.pre-commit-config.yaml` | ruff + ruff-format + local mypy/validate/pytest hooks present |
| 9 | CI runs all gates | `.github/workflows/validate.yml` | pip install `.[dev]`; ruff, format, mypy, pytest+cov, validate, freshness gate; SKIP flags set |
| 10 | README regression guard | `git diff README.md` | clean (untouched) |

## Spec → implementation map
- **Output Freshness Gate** → `.github/workflows/validate.yml` "Output freshness" step.
- **Ruff lint/format** → `[tool.ruff]` in pyproject + CI steps.
- **mypy** → `[tool.mypy]` + `generators/__init__.py` + CI step.
- **Coverage** → `addopts --cov-fail-under=80`; measured baseline 82%.
- **Pre-commit** → `.pre-commit-config.yaml`.
- **Link validation** → `generators/links.py` + `tests/test_links.py` + validate.py wiring.

## Notes / non-blocking
- `apps/portfolio/` (Node) and `cv/` (RenderCV) are tracked in-repo but OUT OF SCOPE for these Python gates; excluded from ruff/mypy/pytest.
- Link/icon reachability checks are network-dependent → warn-only and skipped in CI (`SKIP_ICON_CHECK`/`SKIP_LINK_CHECK`).

## Next: sdd-archive.
