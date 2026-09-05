# Apply Progress: add-platform-specific-data-variety

**Status**: done
**Mode**: Strict TDD
**Final pytest result**: 16 passed in 0.02s

---

## Completed Tasks

All 26 tasks complete.

- [x] 1.1 pyproject.toml created with pytest scaffold config
- [x] 1.2 tests/__init__.py and tests/conftest.py created
- [x] 1.3 tests/fixtures/about_minimal.json and about_full.json created
- [x] 1.4 Scaffold verified: 0 tests, no import errors
- [x] 2.1 RED: test_legacy_about_validates() written
- [x] 2.2 GREEN: monkeypatching wired in test_schema.py
- [x] 2.3 RED→GREEN: test_typed_fields_validate() + test_wrong_type_fails()
- [x] 3.1 RED: test_summary_present() confirmed walrus-in-list bug (FAIL at index 2)
- [x] 3.2 GREEN: walrus bug fixed in generate_github_readme.py render_about()
- [x] 3.3 RED→GREEN: test_summary_absent_falls_back_to_headline() + test_summary_null_falls_back_to_tagline()
- [x] 4.1 compute_headline() interface designed
- [x] 4.2 RED: 3 LinkedIn tests written (all FAIL — function missing)
- [x] 4.3 GREEN: compute_headline() added to generate_linkedin.py; main() updated
- [x] 5.1 compute_cv_headline() interface designed
- [x] 5.2 RED: 3 CV tests written (all FAIL — function missing)
- [x] 5.3 GREEN: compute_cv_headline() added to generate_cv.py; main() line 111 updated
- [x] 6.1 RED: 4 portfolio validation tests written (all FAIL — function missing)
- [x] 6.2 GREEN: validate_portfolio_highlights() added to validate.py; main() wired
- [x] 7.1 ## Platform-Specific Fields section added to README.md
- [x] 8.1 pytest -q: 16 passed
- [x] 8.2 validate.py against real data: all PASS, no portfolio warnings
- [x] 8.3 All generators run successfully, output unchanged (null fields → fallback)
- [x] 8.4 All tasks marked; open questions resolved

---

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1–2.2 | `tests/test_schema.py` | Unit | N/A (new) | Written (monkeypatch wired) | PASS 1/1 | Skipped (schema already correct, single path) | None needed |
| 2.3 | `tests/test_schema.py` | Unit | ✅ 1/1 | Written | PASS 3/3 | 2 cases (valid + wrong type) | None needed |
| 3.1 | `tests/test_generate_github_readme.py` | Unit | N/A (new) | FAIL confirmed (walrus bug at index 2) | — | — | — |
| 3.2 | `tests/test_generate_github_readme.py` | Unit | N/A (new) | ✅ Written | PASS 1/1 (after bug fix) | — | None needed |
| 3.3 | `tests/test_generate_github_readme.py` | Unit | ✅ 1/1 | Written | PASS 3/3 | 3 cases (summary / headline / tagline) | None needed |
| 4.2 | `tests/test_generate_linkedin.py` | Unit | N/A (new) | FAIL confirmed (AttributeError) | — | — | — |
| 4.3 | `tests/test_generate_linkedin.py` | Unit | N/A (new) | ✅ Written | PASS 3/3 | 3 cases (present/truncated/absent) | None needed |
| 5.2 | `tests/test_generate_cv.py` | Unit | N/A (new) | FAIL confirmed (AttributeError) | — | — | — |
| 5.3 | `tests/test_generate_cv.py` | Unit | N/A (new) | ✅ Written | PASS 3/3 | 3 cases (present/absent/null) | None needed |
| 6.1 | `tests/test_validate_portfolio.py` | Unit | N/A (new) | FAIL confirmed (AttributeError) | — | — | — |
| 6.2 | `tests/test_validate_portfolio.py` | Unit | N/A (new) | ✅ Written | PASS 4/4 | 4 cases (valid/unmatched/over6/null) | None needed |

### Test Summary

- **Total tests written**: 16
- **Total tests passing**: 16 / 16
- **Layers used**: Unit (16), Integration (0), E2E (0)
- **Approval tests** (refactoring): 1 — test_summary_present() captured pre-existing walrus bug behavior before fix
- **Pure functions created**: 3 (compute_headline, compute_cv_headline, validate_portfolio_highlights)

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Created | pytest scaffold with testpaths and pythonpath config |
| `tests/__init__.py` | Created | Empty package marker |
| `tests/conftest.py` | Created | make_about(), make_projects() helpers + fixtures_dir fixture |
| `tests/fixtures/about_minimal.json` | Created | Minimal about fixture (3 required fields only) |
| `tests/fixtures/about_full.json` | Created | Full about fixture with all 5 new fields set |
| `tests/test_schema.py` | Created | 3 schema validation tests |
| `tests/test_generate_github_readme.py` | Created | 3 README render tests (bug confirmation + fallback chain) |
| `tests/test_generate_linkedin.py` | Created | 3 LinkedIn headline tests |
| `tests/test_generate_cv.py` | Created | 3 CV headline tests |
| `tests/test_validate_portfolio.py` | Created | 4 portfolio highlights validation tests |
| `generators/generate_github_readme.py` | Modified | Fixed walrus-in-list bug: extracted github_display before lines list |
| `generators/generate_linkedin.py` | Modified | Added compute_headline(); updated main() to call it |
| `generators/generate_cv.py` | Modified | Added compute_cv_headline(); updated main() cv.headline line |
| `generators/validate.py` | Modified | Added validate_portfolio_highlights(); null-skip in validate_value(); wired into main() |
| `README.md` | Modified | Added ## Platform-Specific Fields documentation section |

---

## Deviations from Design

1. **validate_value null-skip**: The design did not explicitly mention updating `validate_value` to skip `None` values. However, `data/about.json` has all 5 new fields set to `null`, and the original validator raised type errors for them. Added `if value is None: return []` at the top of `validate_value` to implement the spec's "null = not set" semantics. This is required for 8.2 to pass and is consistent with the design's stated convention.

2. **README.md overwriting**: The `generate_github_readme.py` generator overwrites `README.md` on each run, which erases the Platform-Specific Fields documentation section added in task 7.1. The section was re-added after the 8.3 generator run. The repo lacks a separate maintainer-level README; the task specified README.md. This is a known structural limitation — future work could add the section to the generator's output template or create a separate DEVELOPMENT.md.

---

## Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command and result | `.venv/bin/python -m pytest -q` → 16 passed in 0.02s |
| Runtime harness result | `python generators/validate.py` → All validations passed; `generate_github_readme.py`, `generate_linkedin.py`, `generate_cv.py` all ran with no errors and null fields produced identical fallback output |
| Rollback boundary | Revert changes to: `generators/generate_github_readme.py`, `generators/generate_linkedin.py`, `generators/generate_cv.py`, `generators/validate.py`. Delete `pyproject.toml`, `tests/`, `README.md` additions. New null fields in `data/about.json` remain harmless. |

---

## Rollback Boundary

Exact files to revert without affecting unrelated work:
- `generators/generate_github_readme.py` (walrus fix → revert removes the fix but doesn't break fallback logic)
- `generators/generate_linkedin.py` (compute_headline extraction)
- `generators/generate_cv.py` (compute_cv_headline extraction)
- `generators/validate.py` (validate_portfolio_highlights + null-skip + main wiring)
- Delete `pyproject.toml` and `tests/` directory
- The `data/about.json` null fields remain harmless even without the generators — no migration needed.
