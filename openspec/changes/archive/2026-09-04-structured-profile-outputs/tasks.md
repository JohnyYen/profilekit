# Tasks: Structured Profile Outputs

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 320–420 (authored; excludes committed `output/` artifacts) |
| 400-line budget risk | Medium–High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (utils + github_readme redirect + tests) → PR 2 (linkedin expansion + portfolio + tests) → PR 3 (cv dual output + stale file removal + docs) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `utils.py` + github_readme redirect (root README regression guard) | PR 1 | `.venv/bin/python -m pytest -q tests/test_utils.py tests/test_generate_github_readme.py` | `python generators/generate_github_readme.py && ls output/github-readme.md` | Revert `utils.py` creation + revert `generate_github_readme.py` write-path change |
| 2 | LinkedIn full profile + portfolio generator | PR 2 (base = PR 1 branch) | `.venv/bin/python -m pytest -q tests/test_generate_linkedin.py tests/test_generate_portfolio.py` | `python generators/generate_linkedin.py && python generators/generate_portfolio.py && ls output/` | Revert `generate_linkedin.py` and `generate_portfolio.py`; no other files affected |
| 3 | CV dual output + `cv.yml` relocation + stale root removal + `generate_all.py` + README note | PR 3 (base = PR 2 branch) | `.venv/bin/python -m pytest -q tests/test_generate_cv.py` | `python generators/generate_cv.py && ls output/cv.yml output/cv.md` | Revert `generate_cv.py`, restore root `cv.yml` from git, remove `generate_all.py` |

---

## Phase 1: Foundation — `generators/utils.py` + `tests/test_utils.py`

- [x] 1.1 **[RED]** Create `tests/test_utils.py`: write a failing test `test_write_output_creates_dir_and_file(tmp_path)` — asserts `write_output("hello", tmp_path / "out", "x.md")` creates the directory and file with correct content and returns the path.
- [x] 1.2 **[RED]** Add a failing test `test_write_output_overwrites_existing_file(tmp_path)` — asserts calling `write_output` twice overwrites without raising.
- [x] 1.3 **[GREEN]** Create `generators/utils.py` with `OUTPUT_DIR` constant (`ROOT_DIR / "output"`), `load_json(filename, data_dir)` (exits 1 if missing), and `write_output(content, output_dir, filename) -> Path` (`mkdir parents=True, exist_ok=True`).
- [x] 1.4 **[REFACTOR]** Confirm `tests/test_utils.py` green; no I/O leaks outside `tmp_path`.

## Phase 2: Redirect `generate_github_readme.py` → `output/github-readme.md`

- [x] 2.1 **[RED]** Add failing test `test_root_readme_not_written(tmp_path, monkeypatch)` to `tests/test_generate_github_readme.py`: monkeypatch `OUTPUT_DIR` to `tmp_path / "output"` and `DATA_DIR` to a fixture data dir, call `main()`, assert `tmp_path / "README.md"` does NOT exist and `tmp_path / "output" / "github-readme.md"` DOES exist.
- [x] 2.2 **[GREEN]** In `generators/generate_github_readme.py`: import `write_output` from `generators.utils`; replace the inline `load_json` with the shared one; add `OUTPUT_DIR = ROOT_DIR / "output"`; change `main()` to call `write_output(output, OUTPUT_DIR, "github-readme.md")` instead of writing `ROOT_DIR / "README.md"`.
- [x] 2.3 **[REFACTOR]** Run `.venv/bin/python -m pytest -q tests/test_generate_github_readme.py tests/test_utils.py`; all 3 pre-existing + 1 new test must pass.

## Phase 3: LinkedIn Full Profile Expansion

- [x] 3.1 **[RED]** Extend `tests/test_generate_linkedin.py`: add failing tests for `render_linkedin_about(about)` (asserts "About" section present and `about.description` in output), `render_linkedin_experience(experience)` (asserts "Experience" heading and at least one company name), `render_linkedin_education(education)` (asserts "Education" heading and at least one institution), `render_linkedin_skills(skills)` (asserts "Skills" heading and at least one category label).
- [x] 3.2 **[RED]** Add failing test `test_linkedin_full_assembly(monkeypatch, tmp_path)`: monkeypatches `OUTPUT_DIR` and `DATA_DIR`, calls `main()`, asserts `output/linkedin.md` contains `## Headline`, `## About`, `## Current Focus`, `## Experience`, `## Education`, `## Skills` sections in order.
- [x] 3.3 **[RED]** Add failing test `test_linkedin_headline_fallback_when_linkedinHeadline_absent`: `about` with no `linkedinHeadline` field; `compute_headline` must use `headline` or `tagline`. (This already passes — confirm it stays green; document explicitly.)
- [x] 3.4 **[GREEN]** In `generators/generate_linkedin.py`: import `write_output` from `generators.utils`; replace inline `load_json` with shared one; add `OUTPUT_DIR`; extract pure functions `render_linkedin_about(about) -> str`, `render_linkedin_experience(experience) -> str`, `render_linkedin_education(education) -> str`, `render_linkedin_skills(skills) -> str`; rewrite `main()` to assemble all six sections (Headline, About, Current Focus, Experience, Education, Skills) and call `write_output(..., OUTPUT_DIR, "linkedin.md")`.
- [x] 3.5 **[REFACTOR]** Run `.venv/bin/python -m pytest -q tests/test_generate_linkedin.py`; all 3 pre-existing + new tests must pass; `compute_headline` 220-char contract unchanged.

## Phase 4: New `generators/generate_portfolio.py`

- [x] 4.1 **[RED]** Create `tests/test_generate_portfolio.py` with failing tests:
  - `test_compute_portfolio_projects_null_highlights_returns_all`: `highlights=None` → all projects returned in source order.
  - `test_compute_portfolio_projects_absent_highlights_returns_all`: `highlights` not in `about` (empty list passed) → all projects returned.
  - `test_compute_portfolio_projects_filters_and_orders`: `highlights=["C","A"]`, projects `[A,B,C]` → returns `[C,A]`.
  - `test_compute_portfolio_projects_unmatched_skipped_and_warns(capsys)`: `highlights=["X","A"]`, projects `[A]` → returns `[A]`, stderr mentions `"X"`.
  - `test_compute_portfolio_projects_all_unmatched(capsys)`: all highlights unmatched → returns `[]`, warns for each.
  - `test_render_portfolio_includes_name_description_tech`: project with name/description/tech → all three present in output.
  - `test_render_portfolio_url_renders_as_link`: non-empty `url` → markdown link present.
  - `test_render_portfolio_empty_url_no_broken_link`: `url=""` → no empty `()` link.
  - `test_render_portfolio_highlights_rendered_as_list`: project with `highlights` → each as `- item`.
  - `test_compute_portfolio_projects_is_pure`: no file I/O side effects (no tmp_path needed).
  - `test_render_portfolio_is_pure`: returns non-empty string, no file writes.
- [x] 4.2 **[GREEN]** Create `generators/generate_portfolio.py` with:
  - `compute_portfolio_projects(projects: list, highlights: list | None) -> list`: `None`/empty → all; else filter by name in highlights order; unmatched → `warnings.warn` + skip.
  - `render_portfolio(about: dict, projects: list) -> str`: heading, description, per-project (name, description, tech list, url link if non-empty, highlights list).
  - `main()`: `load_json` about + projects, call `compute_portfolio_projects(projects, about.get("portfolioHighlights"))`, `render_portfolio`, `write_output(..., OUTPUT_DIR, "portfolio.md")`.
- [x] 4.3 **[REFACTOR]** Run `.venv/bin/python -m pytest -q tests/test_generate_portfolio.py`; all tests green; `validate_portfolio_highlights` in `validate.py` unchanged.

## Phase 5: CV Dual Output — `render_cv_markdown` + `output/cv.yml` Relocation

- [x] 5.1 **[RED]** Extend `tests/test_generate_cv.py` with failing tests:
  - `test_render_cv_markdown_has_headline_section`: output contains a headline string from `about`.
  - `test_render_cv_markdown_has_experience_section`: output contains "## Experience" and at least one company.
  - `test_render_cv_markdown_has_education_section`: output contains "## Education" and at least one institution.
  - `test_render_cv_markdown_has_skills_section`: output contains "## Skills" and at least one category label.
  - `test_cv_main_writes_cv_yml_to_output(monkeypatch, tmp_path)`: monkeypatches `OUTPUT_DIR` + `DATA_DIR`, calls `main()`, asserts `output/cv.yml` exists.
  - `test_cv_main_writes_cv_md_to_output(monkeypatch, tmp_path)`: same setup, asserts `output/cv.md` exists.
  - `test_cv_main_does_not_write_root_cv_yml(monkeypatch, tmp_path)`: asserts `tmp_path / "cv.yml"` does NOT exist.
- [x] 5.2 **[GREEN]** In `generators/generate_cv.py`: import `write_output` from `generators.utils`; replace inline `load_json` with shared one; add `OUTPUT_DIR`; add `render_cv_markdown(about, experience, education, projects, skills, social) -> str` (headline, experience, education, skills sections); rewrite `main()` to call `write_output(yaml_content, OUTPUT_DIR, "cv.yml")` and `write_output(render_cv_markdown(...), OUTPUT_DIR, "cv.md")`. Root `cv.yml` MUST NOT be written.
- [x] 5.3 **[REFACTOR]** Run `.venv/bin/python -m pytest -q tests/test_generate_cv.py`; all 3 pre-existing + new tests pass; `compute_cv_headline` + `escape_yaml_string` unchanged.

## Phase 6: Committed `output/` Artifacts

- [x] 6.1 Run all five generators against real `data/*.json` to populate `output/`: `generate_github_readme.py`, `generate_linkedin.py`, `generate_portfolio.py`, `generate_cv.py`.
- [x] 6.2 Verify `output/` contains exactly: `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml`.
- [x] 6.3 Verify `output/cv.yml` is semantically equivalent to the pre-existing root `cv.yml` (diff YAML values; structure must match).
- [x] 6.4 Stage and commit the five `output/` files (these are committed artifacts, not gitignored). (Files in output/ ready; user to commit in their workflow.)

## Phase 7: Stale Root File Removal

- [x] 7.1 `git rm linkedin-copy.md` — removes stale root file (content preserved in `output/linkedin.md`). (Files were untracked; deleted with `rm`.)
- [x] 7.2 `git rm cv.yml` — removes stale root file (content preserved in `output/cv.yml`). (Files were untracked; deleted with `rm`.)
- [x] 7.3 Verify `README.md` is still present and unmodified (`git diff README.md` shows no changes).

## Phase 8: Optional `generate_all.py` + Docs Note

- [x] 8.1 Create `generators/generate_all.py`: imports and calls all four generator `main()` functions in sequence (github_readme → linkedin → portfolio → cv); prints a summary line listing the five output paths.
- [x] 8.2 Add a comment block at the top of `generators/generate_all.py` noting that `output/github-readme.md` is the deploy source for the `JohnyYen/JohnyYen` GitHub profile README (manual copy or CI step required; automation is out of scope for this change).

## Phase 9: Full Suite Regression Guard

- [x] 9.1 Run `.venv/bin/python -m pytest -q` — all tests (pre-existing 16 + new suite) must pass. (47 passed)
- [x] 9.2 Confirm no test imports or calls write to `ROOT_DIR / "README.md"` (grep `README.md` in test files; none should appear as a write target). (Only assertion that it does NOT exist)
- [x] 9.3 Confirm `conftest.py` helpers `make_about` and `make_projects` are unchanged (no modifications to existing fixtures).
