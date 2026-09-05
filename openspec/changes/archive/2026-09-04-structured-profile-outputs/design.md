# Design: Structured Profile Outputs

## Technical Approach

Approach A (redirect + new generators). Centralize duplicated plumbing in `generators/utils.py`, redirect every generator to a single committed `output/` directory, add two new render paths (portfolio, cv markdown), and expand LinkedIn to a full profile through testable pure functions. Existing tested behavior (`render_about`, `compute_headline`, `compute_cv_headline`, `validate_portfolio_highlights`) is preserved verbatim. Strict TDD: each new behavior is a pure `render_*`/`compute_*` function with fixture tests before wiring into `main()`.

## Architecture Decisions

| Decision | Choice | Alternatives rejected | Rationale |
|---|---|---|---|
| Shared plumbing | New `generators/utils.py` with `load_json` + `write_output` | Keep 3× duplicated `load_json`; base class | Removes duplication; `write_output` gives one place to `mkdir` the output dir, killing the root-write bug class |
| Output location | Single committed `output/`; `OUTPUT_DIR = ROOT_DIR / "output"` per generator | Per-generator dirs; keep root writes | One reviewable diff surface; RenderCV gets a stable input path |
| CV output | Dual: keep RenderCV YAML (`output/cv.yml`) + new `render_cv_markdown` (`output/cv.md`) | Markdown-only | RenderCV consumes YAML only; markdown is the human-readable companion |
| LinkedIn refactor | Extract `render_linkedin_*` pure fns, keep `compute_headline` | Rewrite inline `main()` | Testability + preserves the 220-char headline contract |
| Function purity | Pure fns return strings; only `write_output` touches disk | Fns write files | Matches existing TDD pattern (dict fixtures, no I/O in unit tests) |

## Data Flow

    data/*.json ──load_json──▶ pure render_*/compute_* ──▶ str ──write_output──▶ output/<file>
                                                                    (mkdir parents=True)

## File Changes

| File | Action | Description |
|---|---|---|
| `generators/utils.py` | Create | `load_json`, `write_output`, `OUTPUT_DIR` helper |
| `generators/generate_github_readme.py` | Modify | Target `output/github-readme.md`; import utils |
| `generators/generate_linkedin.py` | Modify | Full profile via `render_linkedin_*`; target `output/linkedin.md` |
| `generators/generate_cv.py` | Modify | Add `render_cv_markdown`; YAML → `output/cv.yml`; markdown → `output/cv.md` |
| `generators/generate_portfolio.py` | Create | `compute_portfolio_projects`, `render_portfolio` → `output/portfolio.md` |
| `generators/generate_all.py` | Create (optional) | Convenience runner, all generators in sequence |
| `output/*` | Create | Five committed artifacts |
| root `linkedin-copy.md`, `cv.yml` | Delete | Stale; superseded by `output/` |
| root `README.md` | Untouched | Maintainer-owned hub readme |

## Interfaces / Contracts

**utils.py** (each generator keeps its own `SCRIPT_DIR`/`ROOT_DIR`/`DATA_DIR`/`OUTPUT_DIR = ROOT_DIR / "output"` and passes them in):

```python
def load_json(filename: str, data_dir: Path) -> dict | list: ...   # exits(1) if missing
def write_output(content: str, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")
    return path
```

**Per generator** — extract pure fns, keep existing ones; `main()` becomes: load → render → `write_output(..., OUTPUT_DIR, "<file>")`.

- github_readme: reuse existing `render_*`; only swap `main()` write target to `output/github-readme.md`.
- linkedin: add `render_linkedin_about(about)`, `render_linkedin_experience(experience)`, `render_linkedin_education(education)`, `render_linkedin_skills(skills)`; `main()` assembles `[compute_headline, render_linkedin_about, render_linkedin_experience, render_linkedin_education, render_linkedin_skills]` (about includes currentFocus) → `output/linkedin.md`. Sections: Headline, About, Current Focus, Experience, Education, Skills.
- cv: keep all `format_*` + YAML assembly (must stay valid RenderCV YAML) → `output/cv.yml`; add `render_cv_markdown(about, experience, education, projects, skills, social)` → `output/cv.md`.

**portfolio.py**:

```python
def compute_portfolio_projects(projects: list, highlights: list | None) -> list:
    # highlights None/empty -> all projects (order preserved)
    # else -> projects whose name is in highlights, order by highlights;
    #         names with no match are skipped (fallback = ignore unmatched)
def render_portfolio(about: dict, projects: list) -> str:
    # "# Portfolio" + about description + per-project: name, description, tech, url, highlights
```

## Testing Strategy

Runner: `.venv/bin/python -m pytest -q`. Strict TDD (RED before GREEN).

| Layer | What | Approach |
|---|---|---|
| Unit | `compute_portfolio_projects` | null->all, populated->filter+order, unmatched name->skipped |
| Unit | `render_portfolio` | section headers, project fields present |
| Unit | `render_linkedin_*` (each) | field presence per fn + one assembly test |
| Unit | `render_cv_markdown` | section presence, date formatting, highlights |
| Unit | `compute_headline`/`compute_cv_headline`/`validate_portfolio_highlights` | unchanged — existing tests must stay green |
| Integration | `write_output` | single `tmp_path` test: creates missing dir, writes content, returns path |

New/extended test files: `tests/test_generate_portfolio.py` (new), `tests/test_utils.py` (new, `write_output` only), extend `tests/test_generate_linkedin.py`, extend `tests/test_generate_cv.py`. Fixtures via `tests/conftest.py` helpers (`make_about`, `make_projects`).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Pure file reads/writes within the repo only.

## Migration / Rollout

1. Add `utils.py` + tests, redirect generators, add new generators (TDD per step).
2. Run all generators; commit populated `output/` (five files). `output/` is not in `.gitignore`, so no ignore change needed.
3. `git rm` root `linkedin-copy.md` and `cv.yml` (history retained). Update RenderCV pipeline reference to `output/cv.yml`.
4. `generate_all.py` sequence (if added): validate (optional) → github_readme → linkedin → portfolio → cv; independent generators, any order safe.

Rollback: revert the change commit; deleted root files restored from history.

## Open Questions

- None — all resolved in exploration (cv.yml→output/, output/ committed, root cleanup, deploy out of scope).
