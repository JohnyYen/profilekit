# Tasks: Portfolio Data Integration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 380–460 (Python: ~120, TS: ~180, generated JSON: ~100, tests+fixtures: ~120) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Python generator + tests → PR 2: TS consumers + build verify |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Python generator, golden tests, generate_all wiring, committed app data | PR 1 (size:exception) | `uv run pytest -q tests/test_generate_portfolio_data.py tests/test_generate_all.py` | `python -m generators.generate_portfolio_data` from repo root | Delete `generators/generate_portfolio_data.py`, revert `generate_all.py`, restore original `apps/portfolio/app/data/*.json` |
| 2 | TS consumers (SkillsSection, layout, CvSection) + pnpm build verify | PR 2 (stacked on PR 1) | `pnpm --dir apps/portfolio build` (or `tsc --noEmit`) | `pnpm --dir apps/portfolio dev` + manual TUI skills/cv/layout inspection | `git checkout` of `SkillsSection.tsx`, `layout.tsx`, `CvSection.tsx` — no data or Python changes |

---

## Phase 1: Test Infrastructure — RED (TDD)

- [x] 1.1 Create `tests/fixtures/portfolio_data/` directory with input fixtures copied from canonical `data/`: `about_input.json` (full canonical `about.json`), `social_input.json` (full canonical `social.json`), `skills_input.json` (canonical `skills.json` with mixed `string | {name,icon?,iconUrl?}` details), `projects_input.json` (two entries with and without optional fields).
- [x] 1.2 Create golden output fixtures in `tests/fixtures/portfolio_data/`: `about_golden.json` (6-key subset: `username`, `tagline`, `description`, `currentFocus`, `whatIBuild`, `learningJourney`), `social_golden.json` (full passthrough), `skills_golden.json` (full `{categories:[{label,details}]}` passthrough), `projects_golden.json` (4-field shape `{name,description,tech,url}` with `""` defaults for missing fields).
- [x] 1.3 Create `tests/test_generate_portfolio_data.py` with RED failing tests (module does not exist yet):
  - [x] 1.3.1 `test_build_about_returns_six_key_subset` — assert output keys match `{username,tagline,description,currentFocus,whatIBuild,learningJourney}` exactly; extra canonical keys absent.
  - [x] 1.3.2 `test_build_about_values_match_golden` — compare `build_about(about_input)` byte-for-byte against `about_golden.json`.
  - [x] 1.3.3 `test_build_social_passthrough` — compare `build_social(social_input)` against `social_golden.json`.
  - [x] 1.3.4 `test_build_skills_passthrough_preserves_categories` — assert N categories same order, all M details preserved (including mixed string/object entries); compare against `skills_golden.json`.
  - [x] 1.3.5 `test_build_projects_maps_to_four_fields` — assert each entry has exactly `{name,description,tech,url}`; `start_date`/`end_date`/`highlights` absent.
  - [x] 1.3.6 `test_build_projects_defaults_missing_tech_and_url_to_empty_string` — input entry with no `tech`/`url` → output has `tech=""`, `url=""`.
  - [x] 1.3.7 `test_build_projects_preserves_source_order` — output order matches input order.
  - [x] 1.3.8 `test_main_writes_four_files_to_portfolio_data_dir` — monkeypatch `PORTFOLIO_DATA_DIR` to `tmp_path`; call `main()`; assert all four JSON files exist with correct content.
  - [x] 1.3.9 `test_main_exits_nonzero_on_missing_canonical_file` — remove one source file from a temp data dir; assert `SystemExit` with code 1 and descriptive stderr message.
  - [x] 1.3.10 `test_generator_writes_only_to_portfolio_data_dir` (threat boundary RED) — assert no file is written outside `PORTFOLIO_DATA_DIR` during `main()`.
  - [x] 1.3.11 Extend `tests/test_generate_all.py` with a RED test `test_generate_all_writes_portfolio_app_data` — assert the four `apps/portfolio/app/data/*.json` files exist after `generate_all.main()` runs.
- [x] 1.4 Confirm all 1.3.x tests FAIL (RED) with `uv run pytest -q tests/test_generate_portfolio_data.py`; note the 129 existing tests remain green.

## Phase 2: Python Generator — GREEN

- [x] 2.1 Create `generators/generate_portfolio_data.py`:
  - [x] 2.1.1 Define `PORTFOLIO_DATA_DIR = ROOT_DIR / "apps" / "portfolio" / "app" / "data"` as a module constant (single fixed path, no dynamic input).
  - [x] 2.1.2 Implement `build_about(about: dict) -> dict` — return only `{username, tagline, description, currentFocus, whatIBuild, learningJourney}` from input.
  - [x] 2.1.3 Implement `build_social(social: dict) -> dict` — full passthrough (return copy of input).
  - [x] 2.1.4 Implement `build_skills(skills: dict) -> dict` — full passthrough of `{categories:[...]}`.
  - [x] 2.1.5 Implement `build_projects(projects: list) -> list` — map each entry to `{name: p["name"], description: p.get("description",""), tech: p.get("tech",""), url: p.get("url","")}`.
  - [x] 2.1.6 Implement `main()`: use `load_json` from `generators.utils` to load all four canonical source files from `DATA_DIR`; call builders; serialize with `json.dumps(..., ensure_ascii=False, indent=2)`; write via `write_output` to `PORTFOLIO_DATA_DIR`.
  - [x] 2.1.7 Add `if __name__ == "__main__": run(main)` guard using `utils.run`.
- [x] 2.2 Run `uv run pytest -q tests/test_generate_portfolio_data.py` — all tests GREEN.
- [x] 2.3 Run `uv run pytest -q` — full suite ≥ 129 tests green, coverage ≥ 80%.

## Phase 3: Pipeline Wiring

- [x] 3.1 Modify `generators/generate_all.py`:
  - [x] 3.1.1 Add `import generators.generate_portfolio_data as portfolio_data` after the existing generator imports.
  - [x] 3.1.2 Call `portfolio_data.main()` inside `main()` after existing generator calls.
  - [x] 3.1.3 Extend the `output_files` list (or add a separate `app_data_files` list) to print the four `apps/portfolio/app/data/*.json` paths in the run summary.
- [x] 3.2 Run `uv run pytest -q tests/test_generate_all.py` — both existing invocation tests and the new `test_generate_all_writes_portfolio_app_data` test GREEN.
- [x] 3.3 Run `uv run pytest -q` — full suite still green.

## Phase 4: Regenerate Committed App Data

- [x] 4.1 Execute `python -m generators.generate_portfolio_data` from the repository root to write `apps/portfolio/app/data/{about,social,skills,projects}.json` with canonical-derived content.
- [x] 4.2 Verify `apps/portfolio/app/data/about.json` contains the 6-key subset (`username`, `tagline`, `description`, `currentFocus`, `whatIBuild`, `learningJourney`) sourced from canonical.
- [x] 4.3 Verify `apps/portfolio/app/data/skills.json` contains `{categories:[{label,details}]}` shape (not the old bucket shape); confirm mixed `string | object` details are present.
- [x] 4.4 Verify `apps/portfolio/app/data/projects.json` contains the 4-field fallback shape (`name`, `description`, `tech`, `url`) sourced from canonical `data/projects.json`.
- [x] 4.5 Verify `apps/portfolio/app/data/social.json` contains the passthrough (`github`, `linkedin`, `email`, `cvUrl`).
- [x] 4.6 Stage the four generated files for commit (they are generated-but-committed artifacts equivalent to `output/`).

## Phase 5: TypeScript Consumers

- [x] 5.1 Update `apps/portfolio/app/components/tui/sections/SkillsSection.tsx`:
  - [x] 5.1.1 Replace the `SkillsData` interface: `type SkillDetail = string | { name: string; icon?: string; iconUrl?: string }; interface SkillsData { categories: { label: string; details: SkillDetail[] }[]; }`.
  - [x] 5.1.2 Remove the old `{ backend, database, devops, tools, learning }` bucket destructuring and `categories` hard-coded array.
  - [x] 5.1.3 Map `data.categories` directly: render each category's `label` as heading; for each `detail` in `details`, render an `<img>` with `src="https://skillicons.dev/icons?i={detail.icon}"` when `detail.icon` is present, else `<img src={detail.iconUrl}>` when `detail.iconUrl` is present, else render `detail` as plain text string; always render the name alongside the icon.
  - [x] 5.1.4 Confirm `TuiContent.tsx` passes `skillsData` as `any` (no prop-type change needed there); verify the component still renders under `{activeSection === 'skills' && <SkillsSection data={skillsData} />}`.
- [x] 5.2 Update `apps/portfolio/app/layout.tsx`:
  - [x] 5.2.1 Add `import aboutData from './data/about.json'` and `import socialData from './data/social.json'` at top of file.
  - [x] 5.2.2 Derive `title` from `aboutData.username` and `aboutData.tagline` (e.g. `"Terminal Portfolio | ${aboutData.username}"`).
  - [x] 5.2.3 Derive `description` from `aboutData.description`.
  - [x] 5.2.4 Update `authors` and `creator` metadata fields to use `aboutData.username`.
  - [x] 5.2.5 Update JSON-LD `Person.name` to `aboutData.username`, `Person.url` to `siteUrl` constant (keep unchanged), `Person.sameAs` to `[socialData.github, socialData.linkedin]`.
  - [x] 5.2.6 Keep `siteUrl` and `siteName` as local constants (not in canonical data).
- [x] 5.3 Update `apps/portfolio/app/components/tui/sections/CvSection.tsx`:
  - [x] 5.3.1 Add `import aboutData from '../../../data/about.json'` at top.
  - [x] 5.3.2 Add documented constants `const CV_SIZE = "69 KB"` and `const CV_DATE = "2026-07-30"` with a comment: `// Non-canonical: update manually on new CV release.`
  - [x] 5.3.3 Replace hard-coded `"Johny A. Pedraza Romero CV"` with `${aboutData.username} CV`.
  - [x] 5.3.4 Replace hard-coded size/date strings with `CV_SIZE` and `CV_DATE` constants.
  - [x] 5.3.5 Verify `terminal.tsx` imports (`aboutData`, `skillsData`, `socialData` from `../../data/*.json`) are unchanged — paths remain identical; no edit needed.

## Phase 6: Build Verification

- [x] 6.1 Check whether `apps/portfolio/node_modules/` exists; if absent, run `pnpm --dir apps/portfolio install` (or `npm install --prefix apps/portfolio`) to install dependencies before typecheck.
- [x] 6.2 Run `pnpm --dir apps/portfolio build` (Next.js 16 + React 19 build gate). If pnpm is unavailable in the environment, run `npx tsc --noEmit --project apps/portfolio/tsconfig.json` as fallback and note the substitution.
- [x] 6.3 Assert zero TypeScript errors from the new `SkillDetail` union type and `SkillsData` shape consumed by `SkillsSection`.
- [x] 6.4 Assert zero TypeScript errors from the `about.json`/`social.json` imports in `layout.tsx` and `CvSection.tsx` (resolved via `resolveJsonModule: true` in `tsconfig.json`).
- [x] 6.5 Run `pnpm --dir apps/portfolio lint` (eslint-config-next) — zero new errors.
- [x] 6.6 Run final `uv run pytest -q` — full Python suite green, coverage ≥ 80%.
