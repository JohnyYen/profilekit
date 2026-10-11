# Delta for profile-outputs

## MODIFIED Requirements

### Requirement: Output directory as single source of truth

The system SHALL maintain one configured directory, `output_dir` (declared
in `profile.toml`, defaulting to `output/`), as the single destination for
all generated profile artifacts. No generator SHALL write any generated file
to the repository root or to any path outside the configured `output_dir`.
The root `README.md` MUST remain maintainer-owned and MUST NOT be modified
by any generator run.
(Previously: the destination was the hardcoded literal `output/`, not a
configurable `output_dir`)

#### Scenario: All generators run successfully

- GIVEN `output_dir` is configured (or defaults to `output/`)
- WHEN all generators are executed
- THEN the output directory SHALL contain exactly six artifacts:
  `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml`, and
  `manifest.json`

> Amended during verification: the count was five before the output contract
> (R3) added `manifest.json`, which is the authoritative index for the
> artifacts that cannot carry a version of their own.
- AND the root `README.md` SHALL remain byte-identical to its pre-run state

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

## ADDED Requirements

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
