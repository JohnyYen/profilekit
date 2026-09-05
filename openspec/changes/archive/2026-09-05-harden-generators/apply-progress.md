# Apply Progress: harden-generators

**Mode**: Strict TDD (RED → GREEN → REFACTOR per task)
**Delivery**: size:exception (single work unit, pre-approved)
**Final pytest count**: 113 passed (76 original + 37 new)
**validate.py**: All 6 files PASS, exit 0
**generate_all dual-invocation**: Both script and module modes exit 0
**README.md**: Untouched

---

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR | Notes |
|------|-----|-------|----------|-------|
| 1.1 test_generate_all.py | FAIL: script invocation exits 1 (ModuleNotFoundError) | — | — | Test written first |
| 1.2 generate_all.py sys.path | — | PASS: both subprocess tests green | — | Bootstrap before package imports |
| 1.3 validate.yml | — | PASS: CI config updated | — | python-version: 3.11, SKIP_ICON_CHECK=1 |
| 1.4 pyproject.toml | — | PASS: jsonschema in runtime deps | — | |
| 2.1 flip test_skills_object_missing_name_invalid | FAIL: assert passed is False (was True) | — | — | |
| 2.2 test_validate_jsonschema.py | FAIL: 1/4 failing (oneOf not enforced) | — | — | |
| 2.3 validate.py rewrite | — | PASS: all 14 schema/validate tests green | Added path to error messages | |
| 3.1 test_utils_errors.py | FAIL: 5/5 ImportError (no DataError/run) | — | — | |
| 3.2 utils.py DataError/run | — | PASS: 5/5 green | — | |
| 3.3 what_i_build helper | — | PASS: immediately green | — | Included in 3.2 commit |
| 3.4 run() in generators | — | PASS: full suite 87 green | — | |
| 4.1 test_icons.py | FAIL: 5/5 ModuleNotFoundError | — | — | |
| 4.2 icons.py | — | PASS: 5/5 green | Fixed monkeypatch for SKIP_ICON_CHECK env isolation | |
| 5.1 test_what_i_build.py | Immediate PASS (what_i_build already present from 3.3) | — | — | |
| 5.3-5.6 generator wiring | — | PASS: goldens captured fresh | — | New output sections as expected |
| 6.1-6.4 golden tests | — | PASS: 5/5 immediately green | — | Captured post-variant wiring |
| 7.1 test_render.py | FAIL: 11/11 ModuleNotFoundError | — | — | |
| 7.2 render.py | — | PASS: 11/11 green | — | Pure functions, no I/O |
| 7.3-7.5 generator refactor | — | PASS: all golden tests stay green | Byte-stable — no golden diff | |

---

## Completed Tasks

All 34 implementation tasks complete (phases 1–8).

---

## Files Created

| File | Description |
|------|-------------|
| `generators/icons.py` | Icon reachability helper (stdlib urllib, SKIP_ICON_CHECK aware) |
| `generators/render.py` | Shared pure formatters: format_date_range, format_experience_entry_yaml/md, format_education_entry_yaml/md |
| `tests/test_generate_all.py` | Subprocess tests for dual invocation |
| `tests/test_validate_jsonschema.py` | jsonschema integration tests (type/required/oneOf/valid) |
| `tests/test_utils_errors.py` | DataError/load_json_strict/run unit tests |
| `tests/test_icons.py` | check_icons unit tests (mocked network) |
| `tests/test_what_i_build.py` | what_i_build fallback matrix tests |
| `tests/test_render.py` | render.py pure helper unit tests |
| `tests/test_golden.py` | Full-output golden snapshot tests |
| `tests/golden/github-readme.md` | Golden snapshot |
| `tests/golden/linkedin.md` | Golden snapshot |
| `tests/golden/cv.md` | Golden snapshot |
| `tests/golden/cv.yml` | Golden snapshot |
| `tests/golden/portfolio.md` | Golden snapshot |

## Files Modified

| File | Description |
|------|-------------|
| `generators/generate_all.py` | Added sys.path bootstrap for script mode |
| `generators/validate.py` | Rewrote internals on jsonschema.Draft7Validator; kept public API |
| `generators/utils.py` | Added DataError, load_json_strict, run(), what_i_build() |
| `generators/generate_github_readme.py` | Added run(), what_i_build section, render.format_date_range |
| `generators/generate_linkedin.py` | Added run(), what_i_build section, render.format_date_range |
| `generators/generate_cv.py` | Added run(), what_i_build section, aliased render.format_*_yaml |
| `generators/generate_portfolio.py` | Added run(), what_i_build section |
| `tests/test_schema.py` | Flipped test_skills_object_missing_name_invalid to assert INVALID |
| `.github/workflows/validate.yml` | Added install + pytest steps; pinned Python 3.11 |
| `pyproject.toml` | Added jsonschema>=4 to runtime dependencies |

---

## Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `SKIP_ICON_CHECK=1 .venv/bin/python -m pytest -q` → **113 passed** |
| Runtime harness | `python generators/generate_all.py` → exit 0; `python -m generators.generate_all` → exit 0; `SKIP_ICON_CHECK=1 python generators/validate.py` → all PASS, exit 0 |
| Rollback boundary | Revert all files under generators/, tests/, .github/workflows/, pyproject.toml; no data or schema files changed |

---

## Deviations from Design

- **Task 3.4**: Generators import `load_json_strict` and `run` but the existing `main()` bodies still use `load_json` for most calls (backward compat). The `run()` wrapper is adopted in `__main__` blocks as specified. This matches the design's intent — no data path changes.
- **Icons test isolation**: Tests (b), (c), (d) were updated to use `monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)` to avoid env-leakage when the full suite runs with `SKIP_ICON_CHECK=1`. This is a test robustness improvement, not a design deviation.
- **CI python**: Pinned to `3.11` (not `3.14`) as specified — jsonschema binary wheels are reliably available for 3.11.
- **format_experience_entry/format_education_entry in generate_cv.py**: Kept as local aliases (`format_experience_entry = format_experience_entry_yaml`) so the call sites inside `main()` remain unchanged and output stays byte-stable.
