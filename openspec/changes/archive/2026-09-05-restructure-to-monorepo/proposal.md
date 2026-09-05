# Proposal: Restructure to Source Monorepo

> **Planning-only.** This proposal defines the target layout and the source/destination split.
> Implementation happens in a LATER change. No code, data, or config is modified here.

## Intent

Profile content is one dataset (`data/*.json`) but its sources are split across 3–4 repos: this
repo, the Next.js portfolio, and the RenderCV pipeline (`my-cv`). Any single content change forces
non-atomic edits and manual cross-repo content sync. The portfolio does NOT import this repo's data;
it carries its OWN divergent, HARDCODED copy of the profile content in `app/data/` as TypeScript
modules. The real friction is that the same content is duplicated and drifts across repos, not that
it is imported. For a single maintainer, monorepo overhead is low and the duplication is the real
cost. Consolidate SOURCES into one repo under the principle **one source, many destinations**.

## Scope

### In Scope
- Adopt target layout: `data/`, `generators/`, `output/`, `schemas/`, `tests/`, `cv/`, `apps/portfolio/`.
- Bring the Next.js portfolio in-repo under `apps/portfolio/` **as-is** (its hardcoded `app/data/`
  TypeScript modules move untouched; it keeps building from its existing internal data). Package
  manager is **pnpm**.
- Bring RenderCV config in-repo under `cv/`.
- Path-scoped CI so Python (`uv`) and Node (`pnpm`) toolchains run independently.

### Out of Scope (Non-Goals)
- **Consolidating the portfolio's hardcoded `app/data/` onto canonical `data/`** — deferred to the
  follow-up change `wire-portfolio-to-canonical-data` (it requires a profile-data-schema ↔
  portfolio-shape mapping). This change moves the portfolio as-is and does NOT touch its data source.
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
None at the spec level. `portfolio-generation` behavior is unchanged, and the portfolio's data
SOURCE is untouched by this change — its hardcoded `app/data/` moves in-repo verbatim and remains
its build-time data source. No import path is repointed here; consolidating that copy onto canonical
`data/` is deferred to `wire-portfolio-to-canonical-data`.

## Approach

Sources are absorbed; platform-forced targets stay thin deploy destinations. Move the portfolio and
CV config in-repo AS-IS (the portfolio keeps its hardcoded `app/data/` and keeps building), and split
CI into path-scoped jobs (`data/**` + `generators/**` + `schemas/**` + `tests/**` + `cv/**` → Python
validate; `apps/portfolio/**` → Node build via `pnpm install --frozen-lockfile && pnpm build`). Use
`git subtree add` from each source's `main` branch to preserve portfolio and CV history when moving
them in.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/portfolio/` | New | Next.js 16 app moved in-repo as-is (pnpm) |
| `cv/` | New | RenderCV config moved in-repo |
| portfolio data source (`app/data/`) | Unchanged | moves in-repo verbatim; still the portfolio's build-time data. Consolidation onto `data/` deferred to `wire-portfolio-to-canonical-data` |
| `.github/workflows/` | Modified | path-scoped Python (`uv`) + Node (`pnpm`) jobs |
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
