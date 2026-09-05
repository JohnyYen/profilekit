# Monorepo Structure Specification

## Purpose

Defines the verifiable structural and behavioral invariants of the consolidated
profile-data monorepo after the `restructure-to-monorepo` change is applied.
The core principle is **one source, many destinations**: profile data lives once
in `data/`; all consumers reference it from that canonical location.

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

No required directory MUST be absent or renamed after the change is applied.

#### Scenario: Layout verified post-restructure

- GIVEN the restructure change has been applied to the repository
- WHEN the repository root is listed
- THEN each of the seven paths above SHALL be present

---

### Requirement: Single source of truth for profile data

`data/*.json` MUST be the sole authoritative store of profile content. No
application or generator inside the repository SHALL maintain a divergent copy
of the profile data.

#### Scenario: Portfolio app reads from in-repo data/

- GIVEN `apps/portfolio/` is the in-repo Next.js application
- WHEN the portfolio application resolves a profile data import
- THEN the import SHALL resolve to a file under `data/` within this repository
- AND no copy of the data SHALL exist under `apps/portfolio/` itself

#### Scenario: No duplicate data files

- GIVEN the restructure has been applied
- WHEN `data/*.json` content is compared to any other JSON files in the repo
- THEN no file outside `data/` SHALL contain a duplicate or divergent copy of profile data

---

### Requirement: In-repo portfolio import via local path

The Next.js portfolio application under `apps/portfolio/` MUST import profile
data via a relative local path (e.g., `../../data/<file>.json`). Cross-repo
fetches, git submodules, and network requests to external repos for profile
data MUST NOT be used.

#### Scenario: Portfolio builds using local path import

- GIVEN `apps/portfolio/` is present and `data/` contains valid JSON files
- WHEN the portfolio build process (e.g., `next build`) is executed inside `apps/portfolio/`
- THEN the build SHALL succeed
- AND no cross-repo fetch or submodule reference SHALL be required to resolve profile data

#### Scenario: Submodule check

- GIVEN the restructure has been applied
- WHEN `.gitmodules` is inspected
- THEN no entry SHALL reference the portfolio repo or profile-data imports as a submodule

---

### Requirement: Path-scoped CI job isolation

The CI configuration MUST gate each toolchain's workflow job with path filters
such that unrelated changes do not trigger unnecessary jobs.

| Triggering path scope | MUST trigger | MUST NOT trigger |
|---|---|---|
| `data/**`, `generators/**`, `schemas/**` | Python data-validation job | Node/portfolio build job |
| `apps/portfolio/**` | Node/portfolio build job | Python data-validation job |

#### Scenario: Data-only change does not trigger portfolio CI

- GIVEN a pull request modifies only files under `data/`
- WHEN CI evaluates path filters
- THEN the Python data-validation job SHALL run
- AND the Node/portfolio build job SHALL NOT run

#### Scenario: Portfolio-only change does not trigger data validation CI

- GIVEN a pull request modifies only files under `apps/portfolio/`
- WHEN CI evaluates path filters
- THEN the Node/portfolio build job SHALL run
- AND the Python data-validation job SHALL NOT run

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
