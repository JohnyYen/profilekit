# Exploration: structured-profile-outputs

## Current State

### Generator Write Targets (Root Paths)

All three generators share the same path-resolution pattern:

```python
SCRIPT_DIR = Path(__file__).resolve().parent   # generators/
ROOT_DIR = SCRIPT_DIR.parent                   # repo root
DATA_DIR = ROOT_DIR / "data"
```

Output is written with `open(ROOT_DIR / "<filename>", "w")`.

| Generator | Writes today | Render functions |
|---|---|---|
| `generators/generate_github_readme.py` | `ROOT_DIR/README.md` (BUG) | `render_about`, `render_skills`, `render_experience`, `render_education`, `render_projects`, `render_social`, `render_social_links` |
| `generators/generate_linkedin.py` | `ROOT_DIR/linkedin-copy.md` | `compute_headline`, `truncate_headline`; rest inline in `main()` |
| `generators/generate_cv.py` | `ROOT_DIR/cv.yml` | `compute_cv_headline`, `escape_yaml_string`, `format_*_entry`, `format_skill_entry` |
| `generators/validate.py` | stdout/stderr only | `validate_file`, `validate_value`, `check_type`, `validate_portfolio_highlights` |

**Known bug**: `generate_github_readme.py` clobbers the maintainer-owned `ROOT_DIR/README.md` on every run. This was flagged as a WARNING in the prior change's archive report. NOTE: the root `README.md` is the *hub repo* README (commit `d6dd9e6` "chore: add README for profile-data hub repo") — it describes this `profile-data` project, and is NOT the GitHub profile README (which is deployed to the special `JohnyYen/JohnyYen` repo).

**Shared duplication**: All three generators have an identical `load_json(filename)` helper loading from `DATA_DIR`. This is a 3× duplication with no shared module.

### Existing Test Scaffold

pytest is fully configured (`pyproject.toml`, `tests/`, `.venv`). 16 tests passing across 5 test files. The established TDD pattern: extract pure `compute_*` / `render_*` functions, pass dict fixtures, no file I/O inside tests.

Test files present:
- `tests/test_generate_github_readme.py` — covers `render_about` (3 tests)
- `tests/test_generate_linkedin.py` — covers `compute_headline` (3 tests)
- `tests/test_generate_cv.py` — covers `compute_cv_headline`, `escape_yaml_string` (3 tests)
- `tests/test_validate_portfolio.py` — covers `validate_portfolio_highlights` (4 tests)
- `tests/test_schema.py` — schema validation tests (3 tests)

### Data Model Summary

| File | Key fields | Status |
|---|---|---|
| `data/about.json` | `username`, `headline`, `tagline`, `description`, `location`, `email`, `phone`, `languages`, `currentFocus[]`, `whatIBuild[]`, `learningJourney`, `githubReadmeSummary`, `linkedinHeadline`, `cvHeadline`, `portfolioHighlights[]`, `whatIBuildVariants` | All 5 platform-specific fields exist but are `null` |
| `data/experience.json` | `company`, `position`, `start_date`, `end_date`, `location`, `summary`, `highlights[]` | 2 entries; sufficient for full LinkedIn experience section |
| `data/education.json` | `institution`, `area`, `degree`, `start_date`, `end_date`, `location`, `summary`, `highlights[]` | 1 entry |
| `data/projects.json` | `name`, `description`, `tech`, `url`, `start_date`, `end_date`, `highlights[]` | 6 entries; `url` may be empty string |
| `data/skills.json` | `categories[].label`, `categories[].details[]` | 7 categories |
| `data/social.json` | `github`, `linkedin`, `email`, `cvUrl` | All populated |
| `data/interests.json` | (empty array) | No data available |
| `data/publications.json` | (empty array) | No data available |

**Data gaps analysis**:

- **Portfolio generator**: No gaps. `projects.json` has all required fields (`name`, `description`, `tech`, `url`, `highlights[]`). `about.json` has `portfolioHighlights` (null-but-present) as the selector, and `validate_portfolio_highlights()` already validates it.
- **Full LinkedIn profile**: No gaps. All sections (headline, about, currentFocus, experience, education, skills) have data.
- **CV markdown (`output/cv.md`)**: No data gaps. Open question is whether `generate_cv.py` also emits RenderCV YAML.

### RenderCV Constraint (Critical)

RenderCV accepts YAML-only input. It cannot consume a `cv.md` markdown file to produce a PDF. The existing `cv.yml` is the pipeline input for the external RenderCV tool that generates the final PDF (`rendercv_output/`).

**RESOLVED (orchestrator + user decision):** `output/` is the single source of truth. `cv.yml` moves to `output/cv.yml` (RenderCV pipeline points there); a human-readable `output/cv.md` is also emitted. Root is never a generation target.

## Proposed Output Layout

```
output/
├── github-readme.md    # from generate_github_readme.py
├── linkedin.md         # from generate_linkedin.py (full structured profile)
├── portfolio.md        # from generate_portfolio.py (NEW)
├── cv.md               # from generate_cv.py (NEW — human-readable markdown)
└── cv.yml              # from generate_cv.py (RenderCV YAML input, relocated from root)
```

## Shared Output Plumbing

`load_json` is duplicated verbatim across all three generators. A small `generators/utils.py` module centralizes loading and output writing:

```python
# generators/utils.py
def load_json(filename: str, data_dir: Path) -> dict | list: ...
def write_output(content: str, output_dir: Path, filename: str) -> Path:
    """Ensure output_dir exists, write content, return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")
    return path
```

All four generators import from `utils` instead of duplicating logic.

## README Resolution

Change `generate_github_readme.py` output path from `ROOT_DIR / "README.md"` to `ROOT_DIR / "output" / "github-readme.md"`. The root `README.md` (hub readme) is then maintainer-owned and never touched by generators. `output/github-readme.md` is intended for deployment to the `JohnyYen/JohnyYen` profile repo.

## Testing Implications Under Strict TDD

| Generator | New pure functions | Test coverage |
|---|---|---|
| `generate_portfolio.py` (new) | `compute_portfolio_projects(projects, highlights)`; `render_portfolio(about, projects)` | 3–4 tests: null highlights (all), populated (filter), unmatched name (fallback) |
| `generate_linkedin.py` (refactor) | `render_linkedin_experience`, `render_linkedin_education`, `render_linkedin_skills`, `render_linkedin_about` | 1–2 tests per fn + assembly test |
| `generate_cv.py` (refactor) | `render_cv_markdown(...)` NEW human-readable path | 3–4 tests: section presence, date formatting, highlights |
| `utils.py` (new) | `write_output` (I/O; single `tmp_path` integration test) | `load_json` covered via generators |

All `compute_*`/`render_*` tests receive dict/list fixtures and assert on returned strings (no file I/O).

## Recommended Approach — A: Redirect + new generators

1. Create `generators/utils.py` (`load_json`, `write_output`).
2. Redirect all three existing generators to `output/`.
3. Add `render_cv_markdown()` to `generate_cv.py`; relocate `cv.yml` emission to `output/cv.yml`.
4. Add `generators/generate_portfolio.py`.
5. Extract render functions in `generate_linkedin.py` for testability and expand to full profile.
6. (Optional, final task) `generators/generate_all.py` convenience wrapper running all generators.

## Open Questions — RESOLVED for this change

1. **cv.yml fate** → `output/cv.yml` (moves into single-source-of-truth `output/`); `output/cv.md` also emitted.
2. **output/ commit strategy** → `output/` is COMMITTED (reviewable outputs for testing).
3. **Root file cleanup** → delete stale root `linkedin-copy.md` and `cv.yml`; leave root `README.md` untouched.
4. **GitHub profile deploy** → out of scope; document that `output/github-readme.md` is the deploy source for `JohnyYen/JohnyYen`.
5. **whatIBuildVariants wiring** → out of scope this change (consistent with prior change); may be used later.

## Ready for Proposal

Yes. All high-priority open questions are resolved by user/orchestrator decision. Proposal encodes scope, the output/ contract, the README fix, and the two new generators.
