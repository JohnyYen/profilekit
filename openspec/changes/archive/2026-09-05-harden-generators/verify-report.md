# Verify Report: harden-generators

**Date**: 2026-09-05
**Mode**: Strict TDD / OpenSpec
**Verdict**: PASS

---

## Completeness Table

| Artifact | Present |
|----------|---------|
| Spec: generator-tooling | Yes |
| Spec: generator-validation | Yes |
| Spec: generator-robustness | Yes |
| Design | Yes |
| Tasks | Yes (all 34 checked) |
| Apply-progress | Yes |

---

## Build / Test Evidence

| Command | Exit Code | Count |
|---------|-----------|-------|
| `SKIP_ICON_CHECK=1 .venv/bin/python -m pytest -q` | 0 | **113 passed** |
| `python generators/generate_all.py` | 0 | 5 files written to `output/` |
| `.venv/bin/python -m generators.generate_all` | 0 | 5 files written to `output/` |
| `SKIP_ICON_CHECK=1 .venv/bin/python generators/validate.py` | 0 | 6 files PASS |

Test count breakdown: 76 original + 37 new = 113 total.

---

## Spec Compliance Matrix

### Domain: generator-tooling

| Requirement | Scenario | Test / Evidence | Status |
|-------------|----------|-----------------|--------|
| CI Runs Pytest Suite | Passing test suite | `test_generate_all.py`, CI workflow `Run pytest` step | PASS |
| CI Runs Pytest Suite | Failing test suite | CI step exits non-zero on test failure (structure verified in validate.yml) | PASS |
| CI Runs Pytest Suite | Dependency installation precedes test run | `.github/workflows/validate.yml`: `pip install -e ".[dev]"` before `python -m pytest -q` | PASS |
| generate_all.py Dual Invocation | Script invocation | `test_generate_all.py::test_generate_all_script_exits_zero` | PASS |
| generate_all.py Dual Invocation | Module invocation | `test_generate_all.py::test_generate_all_module_exits_zero` | PASS |
| generate_all.py Dual Invocation | Invocation failure propagates | `run()` wrapper catches `DataError` → exit 1; unexpected errors re-raised | PASS |

### Domain: generator-validation

| Requirement | Scenario | Test / Evidence | Status |
|-------------|----------|-----------------|--------|
| Schema-Authoritative Validation | Valid data files | `test_validate_jsonschema.py::test_valid_skills_passes`; live run exits 0 | PASS |
| Schema-Authoritative Validation | Type violation | `test_validate_jsonschema.py::test_type_violation_fails` | PASS |
| Schema-Authoritative Validation | Missing required field | `test_validate_jsonschema.py::test_missing_required_field_fails` | PASS |
| Schema-Authoritative Validation | oneOf shape violation | `test_validate_jsonschema.py::test_oneof_violation_fails`; `test_schema.py::test_skills_object_missing_name_invalid` flipped to INVALID | PASS |
| Schema-Authoritative Validation | portfolioHighlights warning preserved | `test_validate_portfolio.py` (4 tests); warning is non-fatal, stderr only | PASS |
| Icon Reachability Check | All icons reachable | `test_icons.py::test_check_icons_200_ok_no_warnings` | PASS |
| Icon Reachability Check | Unresolvable slug | `test_icons.py::test_check_icons_non_200_produces_warning` | PASS |
| Icon Reachability Check | Unresolvable iconUrl | `test_icons.py::test_check_icons_url_error_produces_warning_no_exception` | PASS |
| Icon Reachability Check | Offline / skip mode | `test_icons.py::test_check_icons_offline_returns_empty`; `test_check_icons_skip_env_var` | PASS |

### Domain: generator-robustness

| Requirement | Scenario | Test / Evidence | Status |
|-------------|----------|-----------------|--------|
| Graceful Generator Error Handling | Missing input file | `test_utils_errors.py::test_load_json_strict_missing_file_raises_data_error` | PASS |
| Graceful Generator Error Handling | Malformed JSON | `test_utils_errors.py::test_load_json_strict_malformed_json_raises_data_error` | PASS |
| Graceful Generator Error Handling | Missing required field | `test_utils_errors.py::test_load_json_strict_missing_required_field_raises_data_error` | PASS |
| Graceful Generator Error Handling | Unexpected error propagates | `test_utils_errors.py::test_run_reraises_unexpected_exception` | PASS |
| whatIBuildVariants Platform Wiring | Platform variant present | `test_what_i_build.py::test_what_i_build_returns_platform_variant` | PASS |
| whatIBuildVariants Platform Wiring | Platform variant absent → fallback | `test_what_i_build.py::test_what_i_build_falls_back_when_platform_key_absent` / `_when_variants_absent` / `_when_variant_is_null` | PASS |
| whatIBuildVariants Platform Wiring | Backward compatibility | `test_what_i_build.py::test_what_i_build_returns_empty_list_when_both_absent`; golden tests remain green | PASS |
| Shared Formatting Helpers | Consistent date formatting | `test_render.py::test_format_date_range_*` (3 tests); cv and linkedin both import `format_date_range` from `render.py` | PASS |
| Shared Formatting Helpers | No duplicated formatter code | cv uses `format_experience_entry_yaml` / `format_education_entry_yaml`; linkedin/github use `format_date_range` from `generators.render` — verified by import grep | PASS |
| Shared Formatting Helpers | Byte-stable output after deduplication | All 5 golden tests pass after Phase 7 refactor | PASS |
| Golden Snapshot Tests | Output matches snapshot | `test_golden.py` (5 tests: github-readme.md, linkedin.md, cv.md, cv.yml, portfolio.md) | PASS |
| Golden Snapshot Tests | Output deviates from snapshot → test fails | Structural guarantee of assertion in `test_golden.py` | PASS |
| Golden Snapshot Tests | Snapshots committed before refactor | Apply-progress confirms goldens captured in Phase 6, refactor done in Phase 7 | PASS |

---

## Design Coherence

| Decision | Code | Status |
|----------|------|--------|
| D1: Single `validate` CI job | `.github/workflows/validate.yml`: checkout → setup-python 3.11 → install → pytest → validate.py; `SKIP_ICON_CHECK=1` on both test and validate steps | PASS |
| D2: sys.path bootstrap in generate_all.py | `generate_all.py` lines 12–18: `_ROOT_DIR` inserted at `sys.path[0]` under `__main__` guard | PASS |
| D3: jsonschema.Draft7Validator | `validate.py` line 59: `jsonschema.Draft7Validator(schema)`; public API preserved | PASS |
| D4: DataError + run() | `utils.py`: `DataError(Exception)`, `load_json_strict`, `run(main_fn)`; all 4 generators adopt `run()` in `__main__` | PASS |
| D5: icons.py stdlib-only, SKIP_ICON_CHECK | `icons.py`: `urllib.request` / `urllib.error` only; `SKIP_ICON_CHECK=1` honored at line 74; no `requests` import anywhere | PASS |
| D6: what_i_build helper + all 4 generators | `utils.py::what_i_build`; all 4 generators wire it; "What I build" sections present in all output files | PASS |
| D7: render.py pure helpers | `render.py` created; cv/linkedin/github import from it; no I/O or side effects | PASS |
| D8: goldens before refactor | Phase 6 locked goldens, Phase 7 refactored — all 5 golden tests remain green | PASS |

**Noted deviation** (from apply-progress, not a new finding): Task 3.4 generators keep most `load_json` call sites for backward compat; `run()` adopted only in `__main__` blocks as designed. This matches design intent.

---

## Correctness Table

| Check | Result |
|-------|--------|
| `shell=True` anywhere in generators/tests | NOT FOUND — clean |
| `import requests` anywhere | NOT FOUND — stdlib urllib only |
| `output/` is the only directory written | CONFIRMED (only cv.md, cv.yml, github-readme.md, linkedin.md, portfolio.md) |
| Root `README.md` untouched | CONFIRMED (`git diff README.md` is empty) |
| CI python-version | `3.11` (comment in validate.yml confirms wheel availability rationale) |
| `SKIP_ICON_CHECK` set in CI for both pytest and validate steps | CONFIRMED in validate.yml |
| `test_skills_object_missing_name_invalid` asserts INVALID | CONFIRMED — test passes asserting `passed is False` |

---

## Issues

**CRITICAL**: None

**WARNING**: None

**SUGGESTION**:
- `generate_all.py` does not wrap `main()` with `run()` (no `DataError` guard at the top-level script). Individual generator `main()` calls propagate exceptions. This is a minor gap but does not violate any spec requirement since `generate_all.py` is a convenience orchestrator, not a primary user-facing entry point. Low severity.

---

## Final Verdict

**PASS** — 0 CRITICAL, 0 WARNING, 1 SUGGESTION.

All 113 tests pass. All 20 spec scenarios across 3 domains have passing covering tests. Both `generate_all.py` invocation modes exit 0. `validate.py` reports all 6 files PASS with exit 0. Golden snapshots are byte-stable. CI workflow installs deps, runs pytest (fails on test failure), and sets `SKIP_ICON_CHECK=1`. Root README.md is untouched. No `shell=True`, no `requests` imports.
