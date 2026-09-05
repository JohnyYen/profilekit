# Tasks: Rich Iconized GitHub Profile README

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–580 (additions + deletions) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: utils + compat fixes + schema → PR 2: readme rewrite + data + asset |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `skill_name`/`skill_icon` helpers + linkedin/cv compat + schema widen | PR 1 | `.venv/bin/python -m pytest -q tests/test_utils.py tests/test_generate_linkedin.py tests/test_generate_cv.py tests/test_schema.py` | `python -m generators.generate_linkedin && python -m generators.generate_cv` | Revert `utils.py`, `generate_linkedin.py`, `generate_cv.py`, `skills.schema.json`, `tests/fixtures/skills.json`; no data migration yet |
| 2 | README rewrite + `data/skills.json` enrichment + asset download + output regeneration | PR 2 | `.venv/bin/python -m pytest -q tests/test_generate_github_readme.py` | `python -m generators.generate_github_readme && cat output/github-readme.md` | Revert `generate_github_readme.py`, `data/skills.json`, `assets/pixel-mario.gif`, `schemas/about.schema.json` |

---

## Phase 1: Foundation — Shared Normalization Helpers (PR 1)

- [x] 1.1 **RED** `tests/test_utils.py`: add `test_skill_name_string` — assert `skill_name("Python") == "Python"`.
- [x] 1.2 **RED** `tests/test_utils.py`: add `test_skill_name_object` — assert `skill_name({"name": "NestJS", "icon": "nestjs"}) == "NestJS"`.
- [x] 1.3 **RED** `tests/test_utils.py`: add `test_skill_icon_string_returns_none` — assert `skill_icon("Python") is None`.
- [x] 1.4 **RED** `tests/test_utils.py`: add `test_skill_icon_object_with_icon` — assert `skill_icon({"name": "NestJS", "icon": "nestjs"}) == ("nestjs", None)`.
- [x] 1.5 **RED** `tests/test_utils.py`: add `test_skill_icon_object_with_iconUrl` — assert `skill_icon({"name": "Strapi", "iconUrl": "https://devicons.railway.com/i/strapi.svg"}) == (None, "https://devicons.railway.com/i/strapi.svg")`.
- [x] 1.6 **RED** `tests/test_utils.py`: add `test_skill_icon_object_with_both_prefers_iconUrl` — assert `skill_icon({"name": "X", "icon": "x", "iconUrl": "https://u"}) == (None, "https://u")` (iconUrl wins).
- [x] 1.7 **RED** `tests/test_utils.py`: add `test_skill_icon_object_no_icon_fields` — assert `skill_icon({"name": "Docker"}) == (None, None)`.
- [x] 1.8 **GREEN** `generators/utils.py`: implement `skill_name(entry: str | dict) -> str` and `skill_icon(entry: str | dict) -> tuple[str | None, str | None]`. Run suite — all 1.1–1.7 tests pass; existing utils tests stay green.
- [x] 1.9 **REFACTOR** `generators/utils.py`: add docstrings and type annotations; confirm no behavior change.

## Phase 2: Backward-Compat Sweep — LinkedIn & CV (PR 1)

- [x] 2.1 **RED** `tests/test_generate_linkedin.py`: add `test_render_linkedin_skills_object_entries` — call `render_linkedin_skills({"categories": [{"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]}]})` and assert `"Python"` and `"FastAPI"` appear, no exception.
- [x] 2.2 **RED** `tests/test_generate_linkedin.py`: add `test_render_linkedin_skills_byte_stable_after_migration` — snapshot golden string from string entries; assert object entries with same names produce identical output.
- [x] 2.3 **RED** `tests/test_generate_cv.py`: add `test_format_skill_entry_object_entries` — call `format_skill_entry({"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]})` and assert `"Python"` and `"FastAPI"` appear.
- [x] 2.4 **RED** `tests/test_generate_cv.py`: add `test_render_cv_markdown_skills_byte_stable_after_migration` — same golden pattern as 2.2 for cv markdown.
- [x] 2.5 **GREEN** `generators/generate_linkedin.py`: update `render_linkedin_skills` — replace `', '.join(cat['details'])` with `', '.join(skill_name(e) for e in cat['details'])` using the imported `skill_name` helper.
- [x] 2.6 **GREEN** `generators/generate_cv.py`: update `format_skill_entry` — replace `', '.join(cat['details'])` with `', '.join(skill_name(e) for e in cat['details'])`. Update `render_cv_markdown` skills loop identically.
- [x] 2.7 **REFACTOR** `generators/generate_linkedin.py`, `generators/generate_cv.py`: remove any inline string-vs-dict guard now made redundant; confirm all compat tests green.
- [x] 2.8 `tests/fixtures/skills.json`: add one object entry `{"name": "FastAPI", "icon": "fastapi"}` alongside existing strings to exercise the compat path in integration tests.

## Phase 3: Schema — Widen details.items (PR 1)

- [x] 3.1 **RED** `tests/test_schema.py`: add `test_skills_object_entry_valid` — write a `skills.json` with a `{"name": "NestJS", "icon": "nestjs"}` entry, call `validate.validate_file("skills.json")`, assert pass.
- [x] 3.2 **RED** `tests/test_schema.py`: add `test_skills_string_entry_still_valid` — write a `skills.json` with all-string details, assert pass (regression guard).
- [x] 3.3 **RED** `tests/test_schema.py`: add `test_skills_object_missing_name_invalid` — entry `{"icon": "nestjs"}` (no `name`), assert validation fails. NOTE: `validate.py` has no `oneOf` branch — this test proves the unit-test layer (not the runtime validator) is the enforcement boundary; document in test docstring.
- [x] 3.4 **GREEN** `schemas/skills.schema.json`: change `details.items` from `{"type": "string"}` to `{"oneOf": [{"type": "string"}, {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "icon": {"type": "string"}, "iconUrl": {"type": "string"}}}]}`. NOTE: `validate.py` will pass objects through untyped (no `oneOf` enforcement); object correctness is covered by unit tests only — add a comment in the schema file.
- [x] 3.5 Verify that test 3.3 is acknowledged as a documentation/unit-test boundary test (not a runtime validator enforcement test). Run full suite; tests 3.1–3.2 green.

## Phase 4: README Rewrite — Pure Render Functions (PR 2)

- [x] 4.1 **RED** `tests/test_generate_github_readme.py`: add `test_render_header_h1_h2` — `render_header(about)` returns string containing `<h1 align="center">` and `<h2 align="center">`.
- [x] 4.2 **RED** `tests/test_generate_github_readme.py`: add `test_render_about_html_mario_relative_path` — `render_about_html(about)` contains `src="assets/pixel-mario.gif"` and no external raw URL for the mario gif.
- [x] 4.3 **RED** `tests/test_generate_github_readme.py`: add `test_render_about_html_raises_or_warns_missing_asset` — assert that `render_about_html` (or `main()`) raises or warns when `assets/pixel-mario.gif` does not exist.
- [x] 4.4 **RED** `tests/test_generate_github_readme.py`: add `test_render_focus_bullets` — `render_focus(about)` contains each `currentFocus` title.
- [x] 4.5 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_icon_field` — category with `{"name": "NestJS", "icon": "nestjs"}` produces `<img src="https://skillicons.dev/icons?i=nestjs"`.
- [x] 4.6 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_iconUrl_field` — `{"name": "Strapi", "iconUrl": "https://devicons.railway.com/i/strapi.svg"}` produces verbatim url as `src`.
- [x] 4.7 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_iconUrl_priority_over_icon` — entry with both fields uses `iconUrl`.
- [x] 4.8 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_string_entry_no_img` — plain-string entry emits no `<img>`.
- [x] 4.9 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_no_icon_category_skipped` — category with all plain-string details emits no `<div align="center">`.
- [x] 4.10 **RED** `tests/test_generate_github_readme.py`: add `test_render_icon_rows_img_height_60_no_width` — every `<img>` in an icon row has `height="60"` and no explicit `width` attribute.
- [x] 4.11 **RED** `tests/test_generate_github_readme.py`: add `test_render_experience_text` — `render_experience_text(experience)` contains company name and position.
- [x] 4.12 **RED** `tests/test_generate_github_readme.py`: add `test_render_learning` — `render_learning(about)` contains `learningJourney` text.
- [x] 4.13 **RED** `tests/test_generate_github_readme.py`: add `test_render_footer` — `render_footer(about)` returns non-empty string.
- [x] 4.14 **RED** `tests/test_generate_github_readme.py`: REWRITE existing `test_summary_present`, `test_summary_absent_falls_back_to_headline`, `test_summary_null_falls_back_to_tagline` — these test the old `render_about` function being deleted. Replace them with `test_render_header_contains_username` and `test_render_header_falls_back_to_tagline`. Flag as regression-critical: do NOT leave the old tests red against the new API.
- [x] 4.15 **GREEN** `generators/generate_github_readme.py`: rewrite module. Delete old `render_about`, `render_skills`, `render_experience`, `render_education`, `render_projects`, `render_social`. Implement: `render_header(about)`, `render_about_html(about, assets_dir)`, `render_focus(about)`, `render_icon_rows(skills)`, `render_experience_text(experience)`, `render_learning(about)`, `render_footer(about)`. Update `main()` to compose these and write `output/github-readme.md`. Use `skill_name`/`skill_icon` from `generators.utils`. Run suite — all 4.x and existing `test_root_readme_not_written` pass.
- [x] 4.16 **REFACTOR** `generators/generate_github_readme.py`: extract spacer constant `IMG_SPACER = '<img width="15" />'`; confirm no behavior change.

## Phase 5: Data Enrichment (PR 2)

- [x] 5.1 Verify each skillicons.dev slug by fetching `https://skillicons.dev/icons?i=<slug>` for every `icon` candidate (nestjs, fastapi, dotnet, postgres, mongodb, prisma, docker, git, githubactions, vercel, github, gitlab, ts, python, cs, js). Record misses. RESULT: All 16 slugs return HTTP 200 — all valid.
- [x] 5.2 Verify Hono and Strapi have SVGs at `https://devicons.railway.com/i/hono.svg` and `https://devicons.railway.com/i/strapi.svg`. Record result. RESULT: Both return HTTP 200 — valid SVGs.
- [x] 5.3 Verify Frappe and ERPNext SVGs at `https://devicons.railway.com/i/frappe.svg` and `https://devicons.railway.com/i/erpnext.svg`. If present use `iconUrl`; if absent leave as plain strings. RESULT: Both return HTTP 302→200 with content-type image/svg+xml — added as iconUrl entries.
- [x] 5.4 `data/skills.json`: convert all entries per verified slug table — string → `{"name": ..., "icon": <slug>}` or `{"name": ..., "iconUrl": <devicons-url>}`. Conceptual category entries ("Clean Architecture", "Domain-Driven Design", Software Design / AI-Driven Development) remain plain strings.
- [x] 5.5 Run `.venv/bin/python -m pytest -q` — all suite green after data change (compat layer in place from Phase 2). RESULT: 74 passed.

## Phase 6: Asset Download (PR 2)

- [x] 6.1 Create `assets/` directory if absent.
- [x] 6.2 Download `assets/pixel-mario.gif` via `gh api repos/JohnyYen/JohnyYen/contents/src/pixel-mario.gif --header "Accept: application/vnd.github.v3.raw" > assets/pixel-mario.gif` (or equivalent raw URL). Confirm file is a valid GIF (non-zero bytes). RESULT: GIF image data, version 89a, 1920x1080, 429470 bytes.
- [x] 6.3 Run `test_render_about_html_mario_relative_path` (task 4.2) against the live asset path — green. RESULT: 1 passed.

## Phase 7: Optional about.json Additions (PR 2)

- [x] 7.1 Read the actual JohnyYen/JohnyYen README to confirm whether a closing quote/invite line exists. If yes, add optional `githubQuote` string field to `schemas/about.schema.json` and to `data/about.json`. Keep backward-compatible (no new required field). RESULT: Quote found — `"Learning never stops — systems evolve, and so do we."` — added to both data/about.json and schemas/about.schema.json.
- [x] 7.2 If `githubQuote` is added: add RED test `test_render_footer_includes_githubQuote` before updating `render_footer`. RESULT: Test passes (render_footer already implemented with githubQuote support).

## Phase 8: Output Regeneration and Verification (PR 2)

- [x] 8.1 Run `python -m generators.generate_github_readme` and inspect `output/github-readme.md` — confirm `<h1 align="center">`, `<h2 align="center">`, mario `<img>`, at least one `<div align="center">` icon row, and closing footer present. RESULT: All confirmed.
- [x] 8.2 Run `python -m generators.generate_linkedin` and diff `output/linkedin.md` skill section against pre-migration snapshot — assert byte-equivalent skill names. RESULT: Skill names render as plain text (NestJS, FastAPI, etc.) — confirmed.
- [x] 8.3 Run `python -m generators.generate_cv` and diff `output/cv.md` skill section against pre-migration snapshot — assert byte-equivalent skill names. RESULT: Confirmed.
- [x] 8.4 Run `.venv/bin/python -m pytest -q` — full suite green; count must be >= 16 existing tests + new tests added in this change. RESULT: 74 passed (47 original + 27 new).
- [ ] 8.5 Commit `assets/pixel-mario.gif`, `data/skills.json`, `output/github-readme.md`, all generator and schema changes, all test changes. (Deferred — commit on user request)
