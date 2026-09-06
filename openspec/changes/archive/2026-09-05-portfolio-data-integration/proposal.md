# Proposal: Portfolio Data Integration

## Intent

The in-repo Next.js app `apps/portfolio/` maintains its OWN copies of profile data
(`apps/portfolio/app/data/*.json`) and hardcodes profile metadata (site title, author,
JSON-LD Person, social URLs, CV title). The monorepo's canonical `data/*.json` is NOT the
source of truth for the portfolio, so profile changes must be applied twice and drift.
Make canonical `data/` the single source that feeds the portfolio, keeping "one source,
many destinations" and all generation inside the Python pipeline.

## Scope

### In Scope
- New `generators/generate_portfolio_data.py`: reads canonical `data/*.json`, WRITES
  `apps/portfolio/app/data/{about,skills,projects,social}.json` in app-consumed shapes.
- Wire it into `generate_all` and `generators/validate.py` awareness; `apps/portfolio/app/data/`
  becomes a committed GENERATED artifact (like `output/`).
- Skills: render canonical `{categories:[{label,details}]}` directly — update
  `SkillsSection.tsx` + TS types (details may be strings or `{name,icon?,iconUrl?}`; render icons
  when present). Generator writes canonical categories shape (no lossy bucket mapping).
- Projects: keep live GitHub fetch as PRIMARY; generator syncs canonical `projects.json` into
  the app fallback shape.
- Metadata: feed `app/layout.tsx` (title, author, description, JSON-LD name/url/sameAs) and
  `CvSection.tsx` (CV title) from canonical `about.json`/`social.json`. Non-canonical values
  (CV size/date) derived or made a small configurable constant — never fabricated.

### Out of Scope
- Full monorepo restructure (archived), deploy automation, Node/pnpm CI beyond existing.
- Terminal UI redesign beyond SkillsSection shape + metadata wiring.
- Adding a JS/TS test framework; TS correctness verified via `pnpm build`/typecheck/eslint.

## Capabilities

### New Capabilities
- `portfolio-data-sync`: Python generator that materializes canonical `data/` into the
  portfolio app's consumed JSON shapes under `apps/portfolio/app/data/`, joined to `generate_all`.

### Modified Capabilities
- None. Existing `portfolio-generation` (output/portfolio.md) is untouched; the new generator
  is a distinct script writing into the app tree.

## Approach

Add a pure-transform generator mirroring existing `generators/` patterns: load canonical JSON,
map to app shapes, write into `apps/portfolio/app/data/`. Consume the canonical skills shape
directly in React instead of lossy buckets. Keep GitHub as project primary with generated
fallback. Drive layout/CV metadata from canonical data. Strict TDD (golden-tested transform).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `generators/generate_portfolio_data.py` | New | Canonical → app data transform (golden-tested) |
| `generators/generate_all.py` | Modified | Register new generator in the run sequence |
| `generators/validate.py` | Modified | Note/validate app-data outputs if relevant |
| `tests/` | New | RED tests + golden fixtures for the transform |
| `apps/portfolio/app/data/*.json` | Generated | Now emitted by the pipeline, committed |
| `apps/portfolio/app/components/tui/sections/SkillsSection.tsx` (+types) | Modified | Consume canonical categories, render icons |
| `apps/portfolio/app/layout.tsx` | Modified | Metadata + JSON-LD from data |
| `apps/portfolio/app/components/tui/sections/CvSection.tsx` | Modified | CV title from data; size/date constant |
| `apps/portfolio/app/components/terminal/terminal.tsx` | Modified (if needed) | Adjust data imports |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Skills icons don't map cleanly to a terminal UI | Med | Render icon-if-present, fall back to text label |
| GitHub-fallback shape mismatch | Med | Map to app fallback shape; extra fields harmless |
| Generator writes outside `output/` into app tree | Med | Distinct script; scope path to `apps/portfolio/app/data/`; golden-tested |
| App stops building | Med | `pnpm build`/typecheck/eslint gate in verify |
| Committed generated app data drifts if generator not re-run | Low | Treat as artifact; regenerate in `generate_all` |
| `pnpm` unavailable in verify env | Low | Document build command; skip-with-note if absent |

## Rollback Plan

Revert the change: delete `generators/generate_portfolio_data.py` and its tests, remove the
`generate_all` wiring, and restore `apps/portfolio/app/data/*.json` plus the TS files
(`SkillsSection.tsx`, `layout.tsx`, `CvSection.tsx`, `terminal.tsx`) from git. No canonical
`data/` or schema changes are made, so revert is a clean git checkout with no data migration.

## Dependencies

- Node/`pnpm` toolchain for portfolio typecheck/build during verify.
- Existing Python pipeline (`generators/utils.py`, `generate_all`) and Strict TDD test setup.

## Success Criteria

- [ ] `generate_all` writes `apps/portfolio/app/data/*.json` from canonical `data/`.
- [ ] Skills render from canonical `categories[]` (icons when present).
- [ ] Projects use GitHub primary with generated canonical fallback.
- [ ] Layout/CV metadata sourced from `about.json`/`social.json`; no fabricated values.
- [ ] Golden tests pass; `pnpm build`/typecheck/eslint succeed.
