# Monorepo Structure Specification

## Purpose

Defines the verifiable structural and behavioral invariants of the consolidated
profile-data monorepo after the `restructure-to-monorepo` change is applied.
The core principle is **one source, many destinations**: profile data lives once
in `data/`; the PIPELINE consumers (generators and the CV config) reference it
from that canonical location.

This spec covers the STRUCTURAL move only. The Next.js portfolio ships its own
hardcoded copy of the profile content under `app/data/` (TypeScript modules);
consolidating that copy onto the canonical `data/` is explicitly DEFERRED to the
follow-up change `wire-portfolio-to-canonical-data` and is NOT resolved here.

## Requirements

### Requirement: Canonical repository layout

The repository MUST contain the following top-level directories at their
documented paths after the restructure is applied:

| Path | Role |
|---|---|
| `data/` | Authoritative profile data (JSON) |
| `schemas/` | JSON Schema contracts |
| `generators/` | Python transform scripts |
| `output/` | Generated artifacts (deploy source) |
| `apps/portfolio/` | Next.js portfolio application |
| `cv/` | RenderCV config |
| `tests/` | Automated test suite |

No required directory SHALL be absent or renamed after the change is applied.
Additional top-level directories (e.g., `assets/`, `openspec/`) MAY exist and
are not constrained by this requirement.

#### Scenario: Layout verified post-restructure

- GIVEN the restructure change has been applied to the repository
- WHEN the repository root is listed
- THEN each of the seven paths above SHALL be present

---

### Requirement: Single source of truth for profile data (pipeline consumers)

`data/*.json` MUST be the sole authoritative store of profile content for the
PIPELINE consumers — the Python generators and the RenderCV config under `cv/`.
No generator, and no CV configuration, SHALL maintain a divergent copy of the
profile data.

**Known, deferred divergence (carve-out):** the Next.js portfolio under
`apps/portfolio/` carries its own hardcoded copy of the profile content in
`app/data/` (TypeScript modules). This copy is a KNOWN, temporary divergence
that this change does NOT resolve; consolidating it onto canonical `data/` is
deferred to `wire-portfolio-to-canonical-data`. For the purposes of THIS
requirement, the portfolio's `app/data/` is explicitly excluded from the
"no divergent copy" obligation.

Generated artifacts are exempt: files under `output/`, build outputs (e.g.,
`apps/portfolio/.next/`, `node_modules/`), and any git-ignored copy of `data/`
synced into an app at build time are DERIVED from `data/` and are not considered
divergent source copies for the purposes of this requirement. The exemption
applies only to derived, git-ignored artifacts — a committed or hand-maintained
copy of the data (outside the deferred portfolio carve-out) remains a violation.

#### Scenario: Portfolio data source is unchanged by the move

- GIVEN `apps/portfolio/` is the in-repo Next.js application moved as-is
- WHEN the portfolio application resolves profile data
- THEN it SHALL continue to resolve data from its own hardcoded `app/data/` TypeScript modules exactly as it did before the move
- AND this change SHALL NOT repoint, rewrite, or delete `app/data/` (consolidation onto `data/` is deferred to `wire-portfolio-to-canonical-data`)

#### Scenario: No duplicate data files among pipeline consumers

- GIVEN the restructure has been applied
- WHEN `data/*.json` content is compared to any other authored (non-generated) JSON files consumed by the generators or the `cv/` config
- THEN no such file outside `data/`, excluding generated artifacts under `output/` and build outputs, SHALL contain a duplicate or divergent copy of profile data
- AND the portfolio's `app/data/` is exempt from this check (deferred divergence)

---

### Requirement: Portfolio moved in-repo and builds

The Next.js portfolio application MUST live under `apps/portfolio/` and MUST
build in-repo via **pnpm** using `pnpm install --frozen-lockfile && pnpm build`,
with no cross-repo dependency, git submodule, or network request to an external
repo required for the build. The portfolio's rendering behavior MUST be
unchanged by the move: it continues to source its content from its own hardcoded
`app/data/` TypeScript modules. This change does NOT impose any obligation to
resolve data from the canonical `data/` directory — that consolidation is
deferred to `wire-portfolio-to-canonical-data`.

#### Scenario: Portfolio builds in-repo via pnpm

- GIVEN `apps/portfolio/` is present with its `package.json` and `pnpm-lock.yaml`
- WHEN `pnpm install --frozen-lockfile && pnpm build` is executed inside `apps/portfolio/`
- THEN the build SHALL succeed
- AND no cross-repo fetch or submodule reference SHALL be required to complete the build

#### Scenario: Submodule check

- GIVEN the restructure has been applied
- WHEN `.gitmodules` is inspected
- THEN no entry SHALL reference the portfolio repo or profile-data imports as a submodule

---

### Requirement: In-repo CV config resolves data locally

The RenderCV configuration under `cv/` MUST derive its profile content from the
in-repo `data/` pipeline (directly or via a generated artifact under `output/`,
such as `output/cv.yml`). The CV config MUST NOT embed a hand-maintained,
divergent copy of profile data, and MUST NOT fetch it cross-repo.

#### Scenario: CV config sources data from the pipeline

- GIVEN `cv/` contains the RenderCV configuration and `data/` holds the profile data
- WHEN the CV artifact is produced
- THEN its profile content SHALL trace back to `data/` (directly or through `output/`)
- AND no divergent copy of profile data SHALL be hand-maintained under `cv/`
- AND no cross-repo fetch SHALL be required to resolve profile data for the CV

---

### Requirement: Path-scoped CI job isolation

The CI configuration MUST gate each toolchain's workflow job with path filters
such that unrelated changes do not trigger unnecessary jobs. The Python
data-validation job runs `uv run pytest -q` plus data validation; the
Node/portfolio build job runs `pnpm install --frozen-lockfile && pnpm build`
against a pinned Node version.

| Triggering path scope | MUST trigger | MUST NOT trigger |
|---|---|---|
| `data/**`, `generators/**`, `schemas/**`, `tests/**` | Python data-validation job (`uv run pytest -q`) | Node/portfolio pnpm build job |
| `apps/portfolio/**` | Node/portfolio pnpm build job (`pnpm install --frozen-lockfile && pnpm build`) | Python data-validation job |
| `cv/**` | Python data-validation job (`uv run pytest -q`) | Node/portfolio pnpm build job |
| A PR touching both a Python-scoped path AND `apps/portfolio/**` | Both jobs | — |

Paths not listed above (e.g., `openspec/**`, root docs) MAY skip both jobs.
`cv/` is grouped with the Python toolchain because RenderCV config is validated
alongside the data pipeline, not the Node build.

#### Scenario: Data-only change does not trigger portfolio CI

- GIVEN a pull request modifies only files under `data/`
- WHEN CI evaluates path filters
- THEN the Python data-validation job (`uv run pytest -q`) SHALL run
- AND the Node/portfolio pnpm build job SHALL NOT run

#### Scenario: Portfolio-only change does not trigger data validation CI

- GIVEN a pull request modifies only files under `apps/portfolio/`
- WHEN CI evaluates path filters
- THEN the Node/portfolio pnpm build job (`pnpm install --frozen-lockfile && pnpm build`) SHALL run
- AND the Python data-validation job SHALL NOT run

#### Scenario: CV-only change triggers the Python toolchain

- GIVEN a pull request modifies only files under `cv/`
- WHEN CI evaluates path filters
- THEN the Python data-validation job (`uv run pytest -q`) SHALL run
- AND the Node/portfolio pnpm build job SHALL NOT run

---

### Requirement: Platform-forced targets remain external deploy destinations

The GitHub profile README repository (`JohnyYen/JohnyYen`) MUST NOT be
absorbed into this monorepo. It SHALL remain an external deploy target that
receives `output/github-readme.md`. CV PDF release infrastructure and portfolio
hosting targets are likewise external and MUST NOT be absorbed.

#### Scenario: GitHub profile README target stays external

- GIVEN `output/github-readme.md` has been generated
- WHEN the deployment step publishes the profile README
- THEN the file SHALL be pushed or copied to the external `JohnyYen/JohnyYen` repo
- AND no directory named `JohnyYen` or a nested GitHub profile README repo SHALL exist inside this monorepo

---

### Requirement: Output directory contract preserved

The `output/` directory MUST remain the sole generated-artifact destination
consumed by external targets. The restructure MUST NOT change the file names or
content contracts established by the `profile-outputs` capability.

#### Scenario: Output artifacts unchanged after restructure

- GIVEN the restructure has been applied and all generators are executed
- WHEN `output/` is listed
- THEN it SHALL contain the same five artifacts as before: `github-readme.md`,
  `linkedin.md`, `portfolio.md`, `cv.md`, and `cv.yml`
- AND their content contracts SHALL be identical to those defined in the
  `profile-outputs` spec

---

### Requirement: Generators pass existing tests after restructure

All existing generator tests MUST continue to pass after the sources are moved
into the monorepo. The restructure MUST NOT alter generator behavior or
`output/` file contracts.

#### Scenario: Generator test suite green post-restructure

- GIVEN the restructure has been applied
- WHEN the full test suite (pytest) is executed
- THEN all previously passing generator tests SHALL pass
- AND no test SHALL fail due to a path or import change introduced by the restructure
