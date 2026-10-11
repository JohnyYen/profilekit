# Profile Outputs Specification

## Purpose

Defines the contract for the committed `output/` directory: which files it MUST contain, what writes to it, and the absolute prohibition against writing to the repository root from any generator.

## Requirements

### Requirement: Output directory as single source of truth

The system SHALL maintain one configured directory, `output_dir` (declared
in `profile.toml`, defaulting to `output/`), as the single destination for
all generated profile artifacts. No generator SHALL write any generated file
to the repository root or to any path outside the configured `output_dir`.
The root `README.md` MUST remain maintainer-owned and MUST NOT be modified
by any generator run.

#### Scenario: All generators run successfully

- GIVEN `output_dir` is configured (or defaults to `output/`)
- WHEN all generators are executed
- THEN the output directory SHALL contain exactly six artifacts:
  `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml`, and
  `manifest.json`
- AND the root `README.md` SHALL remain byte-identical to its pre-run state

> Amended during verification: the count was five before the output contract
> (R3) added `manifest.json`, which is the authoritative index for the
> artifacts that cannot carry a version of their own.

#### Scenario: Root README regression guard

- GIVEN the root `README.md` exists with maintainer-authored content
- WHEN `generators/generate_github_readme.py` runs
- THEN the file written SHALL be `{output_dir}/github-readme.md`
- AND `README.md` in the repository root SHALL NOT be created, overwritten,
  or truncated

#### Scenario: Custom output_dir is honored

- GIVEN `profile.toml` sets `output_dir = "dist/generated"`
- WHEN any generator runs
- THEN its artifact SHALL be written under `dist/generated/`, not under
  `output/`

### Requirement: Output directory auto-creation

The shared `write_output` utility SHALL create the `output/` directory (including any missing parent directories) if it does not exist before writing any file. Callers MUST NOT be required to create `output/` manually before invoking a generator.

#### Scenario: output/ missing before first run

- GIVEN the `output/` directory does not exist
- WHEN any generator calls `write_output`
- THEN `output/` SHALL be created automatically
- AND the target file SHALL be written without error

#### Scenario: output/ already exists

- GIVEN the `output/` directory already exists with prior generated files
- WHEN a generator calls `write_output` for any file in that directory
- THEN existing files MUST NOT be deleted
- AND the targeted file SHALL be overwritten with the new content

### Requirement: Required output artifact set

After a full generator run, `output/` MUST contain the following six files:

| File | Generator | Description |
|---|---|---|
| `github-readme.md` | `generate_github_readme.py` | GitHub profile README content |
| `linkedin.md` | `generate_linkedin.py` | Full LinkedIn structured profile |
| `portfolio.md` | `generate_portfolio.py` | Portfolio of selected projects |
| `cv.md` | `generate_cv.py` | Human-readable markdown CV |
| `cv.yml` | `generate_cv.py` | RenderCV YAML input (relocated from root) |
| `manifest.json` | core | Versioned index of output artifacts |

Each generator MUST write only to its designated file in `output/`.

#### Scenario: Complete artifact set after full run

- GIVEN all generators complete without error
- WHEN `output/` is listed
- THEN all six files SHALL be present: `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml`, and `manifest.json`

### Requirement: output/cv.yml RenderCV compatibility

`output/cv.yml` MUST be a valid RenderCV YAML file with byte-equivalent semantic content to the prior root `cv.yml`. Relocating `cv.yml` from the repository root to `output/cv.yml` MUST NOT alter the YAML content. RenderCV tooling SHALL be configurable to read from `output/cv.yml`.

#### Scenario: cv.yml content preserved after relocation

- GIVEN the root `cv.yml` exists before this change is applied
- WHEN the generator writes `output/cv.yml`
- THEN the YAML structure and values in `output/cv.yml` SHALL be semantically equivalent to the prior root `cv.yml`

#### Scenario: RenderCV reads from new path

- GIVEN `output/cv.yml` exists and root `cv.yml` has been removed
- WHEN RenderCV is invoked pointing at `output/cv.yml`
- THEN it SHALL parse the file without error and produce the same PDF as before

### Requirement: Stale root file removal

The files `linkedin-copy.md` and `cv.yml` at the repository root MUST be deleted as part of this change. These files are superseded by `output/linkedin.md` and `output/cv.yml` respectively. Root `README.md` MUST NOT be deleted.

#### Scenario: Stale files removed

- GIVEN root `linkedin-copy.md` and root `cv.yml` exist before the change is applied
- WHEN the change is applied
- THEN both files SHALL be absent from the repository root
- AND root `README.md` SHALL still be present and unmodified

### Requirement: LinkedIn output — full structured profile

`output/linkedin.md` MUST contain six sections derived from `data/*.json`: headline, about/summary, currentFocus, experience, education, and skills. Each section MUST be rendered by a dedicated, testable pure function in `generate_linkedin.py`.

#### Scenario: Full LinkedIn profile rendered

- GIVEN `data/about.json`, `data/experience.json`, `data/education.json`, and `data/skills.json` are populated
- WHEN `generate_linkedin.py` runs
- THEN `output/linkedin.md` SHALL include all six sections: headline, about/summary, currentFocus, experience, education, and skills
- AND each section SHALL contain the corresponding data from the source JSON files

#### Scenario: Headline falls back when linkedinHeadline is absent

- GIVEN `about.linkedinHeadline` is null or absent
- WHEN the LinkedIn profile is generated
- THEN the headline section SHALL fall back to the existing `compute_headline` / truncation behavior using `about.headline` or `about.tagline`

### Requirement: output/cv.md human-readable CV

`generate_cv.py` MUST produce a human-readable markdown CV at `output/cv.md` in addition to the RenderCV YAML at `output/cv.yml`. `cv.md` SHALL include the same key sections as the YAML (headline, experience, education, skills) in readable markdown format.

#### Scenario: cv.md section presence

- GIVEN all CV data files are populated
- WHEN `generate_cv.py` runs
- THEN `output/cv.md` SHALL contain the candidate's headline, at least one experience entry, at least one education entry, and at least one skills section

### Requirement: Generator output boundary enforcement

No generator MUST write to any path outside its resolved `output_dir`. This
boundary MUST be enforced by an automated test that runs every registered
generator against a sandboxed filesystem and asserts no write occurs outside
the configured `output_dir`.

#### Scenario: Boundary test catches an out-of-bounds write

- GIVEN a generator is modified to write to a path outside the configured
  `output_dir`
- WHEN the boundary enforcement test runs
- THEN the test SHALL fail, identifying the offending generator and path

#### Scenario: All registered generators pass the boundary test

- GIVEN the full set of registered generators
- WHEN the boundary enforcement test runs against a sandboxed `output_dir`
- THEN every generator SHALL write only inside that directory
- AND the test SHALL pass
