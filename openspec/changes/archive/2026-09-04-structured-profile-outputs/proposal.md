# Proposal: Structured Profile Outputs

## Intent

Two problems justify this change now:

1. **README-clobbering bug**: `generate_github_readme.py` writes to root `README.md`, overwriting the maintainer-owned hub readme on every run.
2. **Missing structured outputs**: LinkedIn output is a thin headline-only copy, there is no portfolio output, and no human-readable CV. `cv.yml` sits loosely at root next to stale artifacts (`linkedin-copy.md`).

Success = generators emit a complete, reviewable set of profile artifacts into one committed `output/` directory, and never touch root files again.

## Scope

### In Scope
- Establish `output/` as the single source of truth for all generated artifacts (committed).
- Redirect `generate_github_readme.py` → `output/github-readme.md` (root `README.md` never generated).
- Expand `generate_linkedin.py` → `output/linkedin.md` full structured profile (headline + about/summary + currentFocus + experience + education + skills).
- New `generators/generate_portfolio.py` → `output/portfolio.md` (projects + about + portfolioHighlights).
- Add `render_cv_markdown()` to `generate_cv.py` → `output/cv.md`; relocate RenderCV YAML → `output/cv.yml`.
- New `generators/utils.py` with shared `load_json` + `write_output(content, output_dir, filename)`.
- Delete stale root `linkedin-copy.md` and `cv.yml`.

### Out of Scope
- `whatIBuildVariants` generator wiring.
- GitHub profile deploy automation to `JohnyYen/JohnyYen` (documented, not implemented).
- Populating empty `interests.json` / `publications.json`.

## Capabilities

### New Capabilities
- `profile-outputs`: contract for the committed `output/` directory (five artifacts, single source of truth, no root writes).
- `portfolio-generation`: portfolio markdown from projects + portfolioHighlights selector.

### Modified Capabilities
- None (no prior specs exist under `openspec/specs/`).

## Approach

Approach A from exploration: **redirect + new generators**. Extract shared plumbing into `utils.py`, redirect existing generators to `output/`, add the two new render paths (portfolio, cv markdown), and expand LinkedIn to a full profile via testable pure `render_*` functions. Strict TDD: every behavior lands as a pure function with fixture-driven tests before implementation.

**Why single-source `output/`**: root-scattered outputs caused the README bug and made outputs hard to review/diff. One committed directory removes the clobber class of bugs, makes generated content reviewable in PRs, and gives RenderCV a stable input path.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `generators/utils.py` | New | Shared `load_json` + `write_output` |
| `generators/generate_portfolio.py` | New | Portfolio markdown generator |
| `generators/generate_github_readme.py` | Modified | Target `output/github-readme.md` |
| `generators/generate_linkedin.py` | Modified | Full structured profile |
| `generators/generate_cv.py` | Modified | Add `render_cv_markdown`; YAML → `output/cv.yml` |
| `output/` | New | Five committed artifacts |
| root `linkedin-copy.md`, `cv.yml` | Removed | Stale, superseded by `output/` |
| root `README.md` | Untouched | Maintainer-owned hub readme |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| RenderCV path breaks after `cv.yml` move | Med | Document new `output/cv.yml` input path; verify YAML unchanged |
| LinkedIn expansion regresses headline logic | Low | Preserve `compute_headline`; add assembly tests |
| Deleting root files loses history | Low | Content regenerated into `output/`; git retains history |

## Rollback Plan

Revert the change commit. `output/` files are additive; deleted root files are restored from git history. RenderCV path reverts to root `cv.yml` with the revert.

## Dependencies

- Existing pytest scaffold (16 tests passing) for TDD.
- No new runtime dependencies.

## Success Criteria

- [ ] Root `README.md` unchanged after running all generators.
- [ ] `output/` contains `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml`.
- [ ] `output/linkedin.md` includes all six sections.
- [ ] Root `linkedin-copy.md` and `cv.yml` removed; no generator writes to root.
- [ ] New/expanded behaviors covered by passing pure-function tests.
