# Tasks: Add Platform-Specific Data Variety

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–260 (scaffold ~60, tests ~110, generator wiring ~50, validate.py ~40) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | N/A |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | All platform-specific wiring + tests | PR 1 | `pytest -q` | `python generators/generate_linkedin.py && python generators/generate_cv.py` | Revert generator diffs; null fields remain harmless |

---

## Phase 1: Test Scaffold (prerequisite — no tests exist today)

- [x] 1.1 Create `pyproject.toml` at repo root declaring `[project]` with `name = "profile-data"` and `[project.optional-dependencies] dev = ["pytest>=8"]`; add `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `pythonpath = ["."]`.
- [x] 1.2 Create `tests/__init__.py` (empty) and `tests/conftest.py` with a `fixtures_dir` fixture pointing to `tests/fixtures/` and two fixture helpers: `make_about(overrides={})` returning a minimal valid `about` dict (`username`, `tagline`, `description`) merged with `overrides`, and `make_projects(names=[])` returning a list of `{"name": n}` dicts.
- [x] 1.3 Create `tests/fixtures/` directory with `about_minimal.json` (only required fields: `username`, `tagline`, `description`) and `about_full.json` (all five new fields set to non-null values).
- [x] 1.4 Verify scaffold works: run `pytest -q` (zero tests collected, no import errors).

## Phase 2: Schema Confirmation Tests (RED → GREEN — schema already correct)

- [x] 2.1 RED — Create `tests/test_schema.py`. Write `test_legacy_about_validates()`: load `about_minimal.json` fixture, call `validate.validate_file` with a monkeypatched `DATA_DIR` pointing to `tests/fixtures/`, assert it passes. Run `pytest -q tests/test_schema.py` — expect FAIL (no fixture wiring yet).
- [x] 2.2 GREEN — Wire monkeypatching in `test_schema.py` so `validate.DATA_DIR` and `validate.SCHEMAS_DIR` resolve correctly for fixtures. Confirm `test_legacy_about_validates` passes.
- [x] 2.3 RED → GREEN — Add `test_typed_fields_validate()`: use `about_full.json` fixture; assert `validate_file` passes. Add `test_wrong_type_fails()`: pass `portfolioHighlights` as a string (not array); assert `validate_file` returns `(False, errors)` with a non-empty error list.

## Phase 3: GitHub README Generator Confirmation Tests (RED → GREEN — logic already present, but has a rendering bug)

- [x] 3.1 RED — Create `tests/test_generate_github_readme.py`. Write `test_summary_present()`: call `generate_github_readme.render_about(make_about({"username": "X", "githubReadmeSummary": "My summary"}))`, assert the output contains `"**X** — My summary"` and does NOT contain a bare `"My summary"` line before the formatted line. Run — expect FAIL (current line 39 emits the raw string into `lines` before the formatted line, causing it to appear twice).
- [x] 3.2 GREEN — In `generators/generate_github_readme.py`, fix `render_about`: remove the walrus-assigned value from the `lines` list (it is erroneously emitted as a bare item). Extract `github_display` as a plain assignment above the `lines` list, keeping the formatted line `f"**{about['username']}** — {github_display}"` in place. Re-run test — expect PASS.
- [x] 3.3 RED → GREEN — Add `test_summary_absent_falls_back_to_headline()` and `test_summary_null_falls_back_to_tagline()`: verify fallback chain (`headline` then `tagline`) when `githubReadmeSummary` is absent or null. Confirm both pass after the fix in 3.2.

## Phase 4: LinkedIn Generator Wiring (RED → GREEN)

- [x] 4.1 Extract a pure `compute_headline(about: dict) -> str` function from `generate_linkedin.py`'s `main`: it returns `truncate_headline(raw)` where `raw = about.get('linkedinHeadline') or about.get('headline', about.get('tagline', ''))`. Add a stderr warn when `len(raw) > MAX_HEADLINE_LENGTH`. Do NOT change `main`'s output path logic.
- [x] 4.2 RED — Create `tests/test_generate_linkedin.py`. Write three tests before touching `main`: `test_linkedin_headline_present_within_limit()` asserts `compute_headline({"linkedinHeadline": "Exact"}) == "Exact"`; `test_linkedin_headline_exceeds_220()` asserts `len(compute_headline({...})) <= 220` and that stderr contains a warning; `test_linkedin_headline_absent_falls_back()` asserts `compute_headline({"headline": "H"}) == "H"`. Run — all FAIL (function does not exist yet).
- [x] 4.3 GREEN — Add `compute_headline` to `generators/generate_linkedin.py` as specified in 4.1. Update `main` to call `compute_headline(about)` instead of the inline `truncate_headline(about.get(...))`. Re-run tests — expect all PASS.

## Phase 5: CV Generator Wiring (RED → GREEN)

- [x] 5.1 Extract a pure `compute_cv_headline(about: dict) -> str` function from `generate_cv.py`: returns `escape_yaml_string(about.get('cvHeadline') or about.get('headline', about.get('tagline', '')))`. Do NOT change any other function.
- [x] 5.2 RED — Create `tests/test_generate_cv.py`. Write `test_cv_headline_present()`: assert `compute_cv_headline({"cvHeadline": "Arch Lead"})` equals `escape_yaml_string("Arch Lead")`; `test_cv_headline_absent_falls_back()`: assert `compute_cv_headline({"headline": "H"})` equals `escape_yaml_string("H")`. Run — FAIL.
- [x] 5.3 GREEN — Add `compute_cv_headline` to `generators/generate_cv.py`. Update `main` line 111 to use `compute_cv_headline(about)` in the `cv.headline` YAML line (not under `design:`). Re-run tests — PASS.

## Phase 6: portfolioHighlights Validation (RED → GREEN)

- [x] 6.1 RED — Create `tests/test_validate_portfolio.py`. Write `test_all_highlights_valid()` (all names match `projects.json` fixture — no warnings), `test_highlight_unmatched_warns()` (one name missing — stderr contains warning with the unmatched name), `test_highlights_over_6_warns()` (7 entries — stderr warns about exceeding limit), `test_highlights_null_ok()` (null value — no warning). Run — FAIL (`validate_portfolio_highlights` does not exist).
- [x] 6.2 GREEN — Add `validate_portfolio_highlights(about: dict, projects: list) -> list[str]` to `generators/validate.py`. It returns a list of warning strings (empty = ok): checks if `portfolioHighlights` is a non-null list; warns per unmatched name; warns if `len > 6`. Call it from `main()` after the per-file loop, loading `projects.json`, and print each warning to stderr (non-fatal). Re-run tests — PASS.

## Phase 7: Documentation (data-only, no generator wiring)

- [x] 7.1 Add a `## Platform-Specific Fields` section to `README.md` (the repo README, not the generated profile README) documenting all five fields: their types, how each generator uses them, the `whatIBuildVariants` platform keys (`github`, `linkedin`, `cv`, `portfolio`) and their intended use, and the `portfolioHighlights` ≤6 constraint and fallback behavior. Note that `whatIBuildVariants` has no generator wiring in this change — it is data/documentation only.

## Phase 8: Final Verification

- [x] 8.1 Run `pytest -q` — all tests pass with no warnings.
- [x] 8.2 Run `python generators/validate.py` against real `data/about.json` (all null fields) — all validations PASS, no portfolio warnings.
- [x] 8.3 Run each generator (`generate_github_readme.py`, `generate_linkedin.py`, `generate_cv.py`) against real data and confirm output is unchanged from pre-change behavior (null fields produce identical fallback output).
- [x] 8.4 Mark all tasks `[x]` and confirm no open questions remain open (CV headline decision: `cv.headline` route, approved; `whatIBuildVariants`: data/doc only, confirmed).
