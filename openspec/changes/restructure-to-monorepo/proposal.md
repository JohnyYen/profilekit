# Proposal: Restructure to Source Monorepo

> **Planning-only.** This proposal defines the target layout and the source/destination split.
> Implementation happens in a LATER change. No code, data, or config is modified here.

## Intent

Profile content is one dataset (`data/*.json`) but its sources are split across 3–4 repos: this
repo, the Next.js portfolio, and the RenderCV pipeline (`my-cv`). Any single content change forces
non-atomic edits and manual cross-repo data sync (the portfolio imports `about.json`/`projects.json`
cross-repo). For a single maintainer, monorepo overhead is low and the friction is the real cost.
Consolidate SOURCES into one repo under the principle **one source, many destinations**.

## Scope

### In Scope
- Adopt target layout: `data/`, `generators/`, `output/`, `schemas/`, `tests/`, `cv/`, `apps/portfolio/`.
- Bring the Next.js portfolio in-repo under `apps/portfolio/`.
- Switch portfolio from cross-repo import to local `../../data/*.json`.
- Bring RenderCV config in-repo under `cv/`.
- Path-scoped CI so Python and Node toolchains run independently.

### Out of Scope (Non-Goals)
- Deploy/distribution automation — deferred to a later change `profile-output-distribution`.
- Absorbing `JohnyYen/JohnyYen` — GitHub mandates the profile README repo be named after the
  username; it stays a separate deploy TARGET receiving `output/github-readme.md`.
- `my-cv` pipeline internals (RenderCV rendering/PDF release mechanics).
- Filling in real profile data.
- Absorbing hosting targets (Vercel, CV PDF release) — they receive artifacts, not sources.

## Capabilities

### New Capabilities
None. Structural reorganization; no new behavioral capability.

### Modified Capabilities
None at the spec level. `portfolio-generation` behavior is unchanged; only the portfolio's data
IMPORT PATH changes (cross-repo → local). If the spec references cross-repo import as a requirement,
sdd-spec should confirm and, if so, emit a delta narrowing it to local import.

## Approach

Sources are absorbed; platform-forced targets stay thin deploy destinations. Move portfolio and CV
config in-repo, repoint the portfolio import to local `data/`, and split CI into path-scoped jobs
(`data/**` + `generators/**` → Python validate; `apps/portfolio/**` → Node build). Prefer `git
subtree`/`filter-repo` to preserve portfolio history when moving it in.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/portfolio/` | New | Next.js app moved in-repo |
| `cv/` | New | RenderCV config moved in-repo |
| portfolio data import | Modified | cross-repo → local `../../data/*.json` |
| `.github/workflows/` | Modified | path-scoped Python + Node jobs |
| `JohnyYen/JohnyYen`, hosting, PDF release | Unchanged | remain external deploy targets |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Portfolio build integration breaks | Med | Isolate under `apps/`; validate Node build in path-scoped CI |
| CI cross-triggering across toolchains | Med | Path filters per job |
| Loss of moved app git history | Low | Use `git subtree`/`filter-repo` |
| Scope creep into deploy automation | Med | Explicit non-goal; defer to `profile-output-distribution` |

## Rollback Plan

Layout change is additive and reversible. If integration fails, revert the merge/move commits; the
portfolio and CV config can be extracted back to standalone repos via `git subtree split`. External
targets are untouched, so no consumer is affected during rollback.

## Dependencies

- Access to the portfolio and `my-cv` repos to import history.

## Success Criteria

- [ ] Target layout documented and agreed (this proposal).
- [ ] Portfolio and CV config paths defined under `apps/` and `cv/`.
- [ ] Source/destination split explicit: sources in, targets external.
- [ ] Deploy automation confirmed out of scope (later change).
