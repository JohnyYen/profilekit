# Design: Restructure to Source Monorepo

## Technical Approach

Absorb the external portfolio (Next.js 16 + React 19 + TS + Tailwind v4, **pnpm**) and
CV (RenderCV) SOURCES into this Python data pipeline repo under `apps/portfolio/` and
`cv/`, preserving git history via `git subtree add` from each source's `main` branch.
The portfolio moves **as-is**: its hardcoded `app/data/` TypeScript modules travel
untouched and remain its build-time data source. This change does NOT repoint any data
import — consolidating `app/data/` onto canonical `data/` is DEFERRED to the follow-up
change `wire-portfolio-to-canonical-data`. Split CI into path-scoped jobs so the Python
(`uv`) and Node (`pnpm`) toolchains stay isolated. No generator behavior, `output/`
contracts, or `data/` content change. Planning-only doc; realizes spec `monorepo-structure`.

## Architecture Decisions

### Decision: History-preserving import via `git subtree add`

| Option | Tradeoff | Decision |
|---|---|---|
| `git subtree add --prefix` | Single command per source; full history grafted under prefix; no rewrite of this repo's history; reversible via `subtree split` | **Chosen** |
| `git filter-repo` + merge | Cleaner path rewrite but requires rewriting the source clone, an `--allow-unrelated-histories` merge, and more steps/foot-guns | Rejected |

**Rationale**: Single maintainer, low volume, rollback already specified as `subtree split`.
Subtree is the least-steps path that keeps history and stays reversible.

The real source URLs and branches are now known (both default to `main`):

```
# Portfolio → apps/portfolio/
git remote add portfolio-src https://github.com/JohnyYen/my-portfolio-terminal
git subtree add --prefix=apps/portfolio portfolio-src main   # omit --squash to keep full history

# CV config → cv/
git remote add cv-src https://github.com/JohnyYen/my-cv
git subtree add --prefix=cv cv-src main
```

### Decision: Portfolio data resolution — DEFERRED to `wire-portfolio-to-canonical-data`

**Corrected premise:** the portfolio does NOT import this repo's data cross-repo. Its
personal content is HARDCODED in `app/data/` as TypeScript modules, so there is no JSON
import to "repoint". Consolidating that hardcoded copy onto the canonical `data/*.json`
requires a profile-data-schema ↔ portfolio-shape mapping, which is real design work.

For THIS change, the portfolio moves **as-is**: `app/data/` travels untouched, remains
the portfolio's build-time data source, and the build is validated (`pnpm install
--frozen-lockfile && pnpm build`). No data wiring, prebuild copy, symlink, or path alias
is introduced here.

| Option | Tradeoff | Decision |
|---|---|---|
| Wire portfolio onto canonical `data/` now | Requires schema↔portfolio-shape mapping; couples a structural move to a data refactor | **Deferred** to `wire-portfolio-to-canonical-data` |
| **Move as-is, keep hardcoded `app/data/`** | Zero data-shape risk; build validated unchanged; keeps this change purely structural | **Chosen** |

**Rationale**: The structural move and the data-consolidation refactor are independent
concerns with different risk profiles. Keeping them separate lets this change land as a
mechanical, reversible move while the mapping work is scoped on its own. The portfolio's
`app/data/` remaining as a divergent copy is a KNOWN, temporary divergence acknowledged by
spec `monorepo-structure` (Single source of truth — pipeline consumers carve-out).

### Decision: CV config derives from generated `output/cv.yml`

`generators/generate_cv.py` already emits a complete RenderCV `output/cv.yml` from
`data/`. `cv/` holds only the RenderCV pipeline/render config; the data-bearing YAML is
copied/referenced from `output/cv.yml`, never hand-edited under `cv/`.

**Rationale**: Zero divergent copy (spec Req 4); `data/` → `generate_cv.py` → `output/cv.yml`
is the single trace path. Rejected: authoring a second YAML in `cv/` (divergent source).

### Decision: Keep `apps/portfolio/` standalone with its own pnpm lockfile (no root workspace)

The portfolio already ships a `pnpm-lock.yaml` and a `pnpm-workspace.yaml`. Both travel
with it verbatim via `git subtree add`, so its pnpm toolchain arrives self-contained.

| Option | Tradeoff | Decision |
|---|---|---|
| Promote to a root pnpm workspace | Root `package.json`/lockfile couples the Node toolchain into a Python-first repo; CI matrix complexity for one app | Rejected (future option) |
| **Standalone `apps/portfolio/`** | Self-contained `package.json` + `pnpm-lock.yaml` + existing `pnpm-workspace.yaml`; Python (`uv`) and Node (`pnpm`) toolchains fully isolated | **Chosen** |

**Rationale**: One Node app, one maintainer — a root workspace adds coupling for no reuse
benefit and would pull pnpm into the repo root. Keeping the portfolio standalone isolates
the Node toolchain from this Python-first repo. The portfolio's own `pnpm-workspace.yaml`
stays inside `apps/portfolio/` and is scoped to that app. If a second Node app appears
later, promoting to a root workspace is a separate change.

## Data Flow

Source absorption (one-time):

    portfolio repo ──subtree add──→ apps/portfolio/   (history preserved)
    my-cv repo     ──subtree add──→ cv/               (history preserved)

Build flow (steady state):

    data/*.json ──→ generators/ ─→ output/{github-readme,linkedin,portfolio,cv}.md, cv.yml
                                          └─ output/cv.yml ─→ cv/ (RenderCV render → PDF, external release)

    apps/portfolio/app/data/ (hardcoded TS, in-repo) ─→ pnpm build ─→ .next/ (external hosting)

Note: the portfolio's `app/data/` is NOT yet fed by canonical `data/` — that link is
deferred to `wire-portfolio-to-canonical-data`. Today it is an independent, divergent copy.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/portfolio/**` | Create (subtree) | Next.js 16 app grafted with history, as-is (incl. `app/data/`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`) |
| `cv/**` | Create (subtree) | RenderCV config grafted with history |
| `apps/portfolio/app/data/` | Unchanged | hardcoded TS data moves verbatim; NOT repointed (deferred) |
| `.github/workflows/validate.yml` | Modify | add `paths:` filter → Python job (`uv run pytest -q`) |
| `.github/workflows/portfolio.yml` | Create | path-scoped Node build job (`pnpm install --frozen-lockfile && pnpm build`) |

## Interfaces / Contracts

Path-scoped CI (spec Req 5). Two workflows, disjoint `paths:` filters; a PR touching both
scopes triggers both (GitHub OR-evaluates per workflow).

```yaml
# .github/workflows/validate.yml (Python + cv)
on:
  pull_request:
    paths: ['data/**','generators/**','schemas/**','tests/**','cv/**']
# steps: uv sync; uv run pytest -q; uv run python generators/validate.py

# .github/workflows/portfolio.yml (Node / pnpm)
on:
  pull_request:
    paths: ['apps/portfolio/**']
# steps: setup-node (pinned version) + pnpm/action-setup;
#        pnpm install --frozen-lockfile; pnpm build   (working-directory: apps/portfolio)
```

`cv/**` maps to the Python job (RenderCV config validated with the data pipeline, not Node).

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Generators unchanged | Existing `uv run pytest -q` (113 tests) stays green (spec Req 8) |
| Integration | `output/` 5-artifact contract | Assert names/content post-move (spec Req 7) |
| Integration | Portfolio builds in-repo | `pnpm install --frozen-lockfile && pnpm build` succeeds inside `apps/portfolio/`; no cross-repo fetch/submodule (Portfolio-builds Req) |
| Integration | Portfolio data source unchanged | `app/data/` present and untouched; rendering behavior unchanged (deferred-divergence carve-out) |
| Integration | No submodule / duplicate pipeline data | `.gitmodules` absent portfolio; no divergent authored JSON among generator/`cv` consumers, portfolio `app/data/` exempt (Single-source Req) |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary introduced. `git subtree` and CI YAML are one-time/declarative
operational steps, not runtime-invoked shell/process integration in the pipeline.

## Migration / Rollout

Additive and reversible. Import via `subtree add` (history preserved), then add path-scoped
CI in follow-up commits. No data import is repointed here (that is deferred to
`wire-portfolio-to-canonical-data`). Rollback: revert merge/move commits or extract via
`git subtree split --prefix=apps/portfolio` / `--prefix=cv` back to standalone repos.
External targets (`JohnyYen/JohnyYen`, hosting, PDF release) untouched.

## Follow-ups / Next Steps

- **`wire-portfolio-to-canonical-data`** — refactor the portfolio to consume the canonical
  `data/*.json`, dropping the hardcoded `app/data/` TypeScript modules. This change OWNS the
  profile-data-schema ↔ portfolio-shape mapping and resolves the deferred divergence.
- `profile-output-distribution` — deploy/distribution automation (separate, already noted).
- Future option: promote `apps/portfolio/` to a root pnpm workspace if a second Node app appears.

## Open Questions

All prior premises are now resolved by verified ground truth:

- Source URLs/branches: `https://github.com/JohnyYen/my-portfolio-terminal` → `apps/portfolio/`
  and `https://github.com/JohnyYen/my-cv` → `cv/`, both from `main`.
- Portfolio data mechanism: content is HARDCODED in `app/data/` (TypeScript), not imported —
  no repoint needed here; consolidation deferred to `wire-portfolio-to-canonical-data`.
- Package manager: **pnpm** (`pnpm-lock.yaml` + `pnpm-workspace.yaml` present); CI uses
  `pnpm install --frozen-lockfile && pnpm build` on a pinned Node version.
