# Tasks: Harden the Profile Generator Pipeline

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650–850 (new files: icons.py ~60, render.py ~80, test_icons.py ~60, test_render.py ~70, test_what_i_build.py ~50, test_generate_all.py ~30, test_golden.py ~80, golden files ~100; modified: validate.py ~150, utils.py +60, generate_all.py +10, 4 generators +80 each, validate.yml +10, pyproject.toml +5, test_schema.py flip ~5) |
| 400-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | Single PR — size:exception pre-approved |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Single size:exception PR covering all 8 tiers | PR 1 (only) | `.venv/bin/python -m pytest -q` | `python generators/generate_all.py && python -m generators.generate_all` | Revert all modified files; no data or schema changes |

---

## Phase 1: CI + Runnability (Foundation)

Spec: CI Runs Pytest Suite · generate_all.py Dual Invocation

- [x] 1.1 **RED** — Write `tests/test_generate_all.py`: assert `subprocess.run(["python", "generators/generate_all.py"], ...)` exits 0; assert `subprocess.run(["python", "-m", "generators.generate_all"], ...)` exits 0 (no `shell=True`). Both tests must FAIL before the fix.
- [x] 1.2 **GREEN** — In `generators/generate_all.py` add under `if __name__ == "__main__":` a `sys.path` bootstrap that inserts `str(ROOT_DIR)` at `sys.path[0]` before any `generators.*` imports execute as script. Keep the existing `main()` call. Confirm both subprocess tests pass.
- [x] 1.3 **GREEN** — In `.github/workflows/validate.yml`: after `actions/checkout@v4`, add `pip install -e ".[dev]"` install step; add a `Run pytest` step: `SKIP_ICON_CHECK=1 .venv/bin/python -m pytest -q` (or `python -m pytest -q` if no venv in CI — use `pip install -e ".[dev]"` to make deps available and run `python -m pytest -q`); keep existing `validate.py` step after. Set `python-version: "3.11"` or keep `3.14` — confirm a jsonschema wheel exists; prefer `3.11` for wheel availability.
- [x] 1.4 **GREEN** — In `pyproject.toml`: move `jsonschema>=4` from dev to `[project.dependencies]` (needed at runtime); keep `pytest>=8` in `dev`. Verify `pip install -e ".[dev]"` satisfies both pytest and jsonschema.

---

## Phase 2: Schema-Authoritative Validation

Spec: Schema-Authoritative Validation · portfolioHighlights warning preserved

- [x] 2.1 **RED** — In `tests/test_schema.py` flip `test_skills_object_missing_name_invalid`: change the assertion from `assert passed is True` to `assert passed is False` with a message that the jsonschema validator now enforces `oneOf` inside `skills.schema.json`. This test MUST fail before the validate.py rewrite.
- [x] 2.2 **RED** — Write `tests/test_validate_jsonschema.py` with RED tests: (a) type violation → `passed is False` and error mentions field; (b) missing required field → `passed is False`; (c) oneOf violation (object missing `name`) → `passed is False`; (d) valid data → `passed is True`. All four must fail against current hand-rolled `validate.py`.
- [x] 2.3 **GREEN** — Rewrite `generators/validate.py` internals to use `jsonschema.Draft7Validator`. Keep public surface: `validate_file(filename) -> (bool, list[str])`, `validate_portfolio_highlights(about, projects) -> list[str]`, `main() -> int`, module-level `DATA_DIR` / `SCHEMAS_DIR` monkeypatchable. Data-file→schema map: `about`→`about.schema.json`, `social`→`social.schema.json`, `experience`→`experience.schema.json`, `education`→`education.schema.json`, `projects`→`projects.schema.json`, `skills`→`skills.schema.json`. Errors include file name and jsonschema `message`. Keep PASS/FAIL table + non-zero exit + `validate_portfolio_highlights` stderr warning. Add call to `check_icons` stub (to be implemented in Phase 4 — guard with `try/except ImportError` or import lazily so Phase 2 stays green without icons.py yet).
- [x] 2.4 **VERIFY** — Run `.venv/bin/python -m pytest -q tests/test_schema.py tests/test_validate_jsonschema.py tests/test_validate_portfolio.py` — all green. 76 prior tests still green.

---

## Phase 3: Graceful Error Handling

Spec: Graceful Generator Error Handling

- [x] 3.1 **RED** — Write `tests/test_utils_errors.py`: (a) missing file → `DataError` raised with file path in message, no sys.exit call; (b) malformed JSON → `DataError` with file + parse location; (c) missing required field (via `load_json_strict`) → `DataError` with file+field; (d) `run(main_fn)` calling a fn that raises `DataError` → exits 1 (monkeypatch `sys.exit`); (e) `run(main_fn)` calling a fn that raises `ValueError` → re-raises (not swallowed). All must fail against current `utils.py`.
- [x] 3.2 **GREEN** — In `generators/utils.py` add: `class DataError(Exception): ...` (stores `file`, `field` attrs); `load_json_strict(filename, data_dir, required_fields=()) -> dict|list` — raises `DataError` on missing file, `json.JSONDecodeError` → `DataError`, missing required field → `DataError`; `run(main_fn) -> None` — calls `main_fn()`, catches `DataError` → `print(str(e), file=sys.stderr); sys.exit(1)`, re-raises all other exceptions. Preserve existing `load_json` unchanged for backward compat.
- [x] 3.3 **GREEN** — Add `what_i_build(about: dict, platform: str) -> list[str]` to `generators/utils.py`: returns `[about["whatIBuildVariants"][platform]]` if `whatIBuildVariants` key exists, is non-null, and `platform` key is non-null; else returns `about.get("whatIBuild", [])`. No exception if keys absent.
- [x] 3.4 **GREEN** — Adopt `run()` wrapper in each generator's `if __name__ == "__main__"` block: `generators/generate_github_readme.py`, `generators/generate_linkedin.py`, `generators/generate_cv.py`, `generators/generate_portfolio.py`. Each generator's `main()` should use `load_json_strict` for its primary data files (about, experience, education, etc.) — replace existing `load_json` calls that would emit `sys.exit`. Keep fallback fields accessed via `.get()` with defaults (those are optional, not strict).
- [x] 3.5 **VERIFY** — `.venv/bin/python -m pytest -q tests/test_utils_errors.py` all green; existing tests still 76 green.

---

## Phase 4: Icon Reachability Helper

Spec: Icon Reachability Check

- [x] 4.1 **RED** — Write `tests/test_icons.py`: (a) `check_icons(skills, offline=True)` returns `[]` and makes no network calls; (b) mocked `urllib.request.urlopen` returning status 200 → `[]` warnings; (c) mocked non-200 response → list contains warning string with slug/URL; (d) mocked `urllib.error.URLError` (timeout) → list contains warning, no exception raised; (e) `SKIP_ICON_CHECK=1` env var → returns `[]` without network (monkeypatch `os.environ`). All must fail before `icons.py` exists.
- [x] 4.2 **GREEN** — Create `generators/icons.py` with `check_icons(skills: dict, *, offline: bool = False) -> list[str]`. Uses only stdlib `urllib.request` / `urllib.error` (no `requests`). For each category → detail entry with a slug or `iconUrl`: issue HEAD request (fallback GET on `405`); non-200 or `URLError` → append warning string; timeout=5s. Skipped entirely when `offline=True` OR `os.environ.get("SKIP_ICON_CHECK") == "1"`. Never raises.
- [x] 4.3 **GREEN** — Wire `check_icons` in `generators/validate.py` `main()`: import from `generators.icons`; call after schema loop; print each warning to stderr. Guard with `SKIP_ICON_CHECK` env check at call site (already inside `check_icons` but explicit guard at validate.py level is fine too).
- [x] 4.4 **VERIFY** — `.venv/bin/python -m pytest -q tests/test_icons.py` all green; full suite still green.

---

## Phase 5: whatIBuildVariants Wiring

Spec: whatIBuildVariants Platform Wiring

- [x] 5.1 **RED** — Write `tests/test_what_i_build.py`: (a) variant present for platform → returns variant value; (b) variant key absent → returns `whatIBuild` list; (c) `whatIBuildVariants` absent → returns `whatIBuild`; (d) variant is null → returns `whatIBuild`; (e) both absent → returns `[]`. Must fail before `what_i_build` exists in utils.py (already added stub in 3.3 — verify tests fail or skip if stub doesn't match yet).
- [x] 5.2 **GREEN** — Confirm `what_i_build` in `generators/utils.py` (added in 3.3) passes all five scenarios from 5.1. Adjust if needed.
- [x] 5.3 **GREEN** — Add "What I build" section to `generators/generate_github_readme.py`: call `what_i_build(about, "github")`; if non-empty, render a `### What I build` markdown section with a bullet per item. Choose placement: after the header block, before "About Me". This produces NEW output — golden will be authored fresh after this step.
- [x] 5.4 **GREEN** — Add `what_i_build(about, "linkedin")` section to `generators/generate_linkedin.py`: if non-empty, render a `## What I Build` section with bullets, placed after the About section.
- [x] 5.5 **GREEN** — Add `what_i_build(about, "cv")` section to `generators/generate_cv.py`: if non-empty, render a short "What I build" note in the summary or as a new YAML section, depending on existing structure. Keep byte-stable for data without the key.
- [x] 5.6 **GREEN** — Add `what_i_build(about, "portfolio")` section to `generators/generate_portfolio.py`: if non-empty, render appropriately. Keep byte-stable for data without the key.
- [x] 5.7 **VERIFY** — `.venv/bin/python -m pytest -q tests/test_what_i_build.py` all green; run all generators manually (`python -m generators.generate_all`) to confirm output files exist and generators exit 0.

---

## Phase 6: Golden Snapshot Tests

Spec: Golden Snapshot Tests · Shared Formatting Helpers (pre-condition)

> Goldens MUST be committed before Phase 7 (dedup refactor). This phase locks current output.

- [x] 6.1 **Setup** — Create `tests/golden/` directory. Run all generators once with canonical `data/` via `python -m generators.generate_all`; copy `output/github-readme.md`, `output/linkedin.md`, `output/cv.md`, `output/cv.yml`, `output/portfolio.md` into `tests/golden/` as committed reference files.
- [x] 6.2 **Write test** — Create `tests/test_golden.py`: parametrize over `[("github-readme.md", generate_github_readme), ("linkedin.md", generate_linkedin), ("cv.md", generate_cv), ("cv.yml", generate_cv), ("portfolio.md", generate_portfolio)]`; run each generator in a tmp dir via monkeypatched `OUTPUT_DIR`; assert generated content == `(GOLDEN_DIR / filename).read_text()`. Add `REGEN_GOLDEN=1 pytest` regen path: if env var set, overwrite golden file instead of asserting.
- [x] 6.3 **RED→GREEN** — Run `pytest tests/test_golden.py` — must be GREEN immediately (goldens were just captured from current canonical output). If any fail, diff and fix the golden capture (do not change generator code here).
- [x] 6.4 **VERIFY** — Commit goldens; full suite still 76+ green.

---

## Phase 7: Shared Formatters (Dedup Refactor)

Spec: Shared Formatting Helpers · Golden Snapshot Tests (byte-stability gate)

> Phase 6 goldens are the safety net. This refactor MUST keep all golden tests green.

- [x] 7.1 **RED** — Write `tests/test_render.py`: unit-test each planned helper: (a) `format_date_range(start, end, default_end="Present")` produces expected string; (b) `format_experience_entry_yaml(entry) -> str` matches expected YAML block; (c) `format_education_entry_yaml(entry) -> str` matches expected YAML block; (d) `format_experience_entry_md(entry) -> str` matches expected markdown block (if linkedin/github use markdown format). Must fail before `render.py` exists.
- [x] 7.2 **GREEN** — Create `generators/render.py` with the extracted pure helpers: `format_date_range`, `format_experience_entry_yaml`, `format_education_entry_yaml`, `format_experience_entry_md`, `format_education_entry_md` (add markdown variants for linkedin/github). All helpers are pure functions (no I/O, no side effects).
- [x] 7.3 **GREEN** — Refactor `generators/generate_cv.py`: replace inline `format_experience_entry`, `format_education_entry` with imports from `generators.render`. Run `pytest tests/test_golden.py -k "cv"` — must stay green.
- [x] 7.4 **GREEN** — Refactor `generators/generate_linkedin.py`: replace inline experience/education formatting with `render.*` helpers. Run `pytest tests/test_golden.py -k "linkedin"` — must stay green.
- [x] 7.5 **GREEN** — Refactor `generators/generate_github_readme.py`: replace any inline date/experience/education formatting with `render.*` helpers. Run `pytest tests/test_golden.py -k "github"` — must stay green.
- [x] 7.6 **VERIFY** — `.venv/bin/python -m pytest -q` — ALL tests green (76+ original + all new). No golden diff.

---

## Phase 8: Final Verification

- [x] 8.1 Run `.venv/bin/python -m pytest -q` — confirm full suite green, no regressions.
- [x] 8.2 Run `python generators/generate_all.py` (script) — exits 0, writes `output/`.
- [x] 8.3 Run `python -m generators.generate_all` (module) — exits 0, byte-identical output.
- [x] 8.4 Run `python generators/validate.py` against real `data/` — all PASS, exit 0, no spurious warnings.
- [x] 8.5 Run `SKIP_ICON_CHECK=1 python generators/validate.py` — icon step skipped, exit 0.
- [x] 8.6 Confirm `output/` is the only directory written; `README.md` at repo root is untouched.
- [x] 8.7 Confirm no `shell=True` in any subprocess call; no `requests` import anywhere (only stdlib `urllib`).

---

## Threat Matrix Coverage

| Row | RED Test Task |
|-----|---------------|
| Outbound network (icon check) | 4.1(c)(d): mocked non-200 / URLError → warning, no raise |
| Subprocess invocation (`generate_all`) | 1.1: `subprocess.run([...])` arg list (no `shell=True`), asserts exit 0 |
| CI command execution | 1.3: `SKIP_ICON_CHECK=1` in CI; pinned deps install before pytest |
