# Delta for Generator Tooling

## MODIFIED Requirements

### Requirement: Output Freshness Gate

The CI workflow MUST regenerate all output artifacts through the generator CLI
by running `python -m generators.cli generate` (which runs every generator in
`generate_all` order) and then MUST fail the build with a non-zero exit code if
the committed `output/` directory differs from the freshly generated output
(verified via `git diff --exit-code -- output/`). Driving regeneration through
the CLI ensures CI exercises the same entry point users run locally; the
underlying `python -m generators.generate_all` invocation remains supported and
byte-identical.

#### Scenario: Committed output matches fresh generation

- GIVEN all data files are valid and the committed `output/` matches what the generator would produce
- WHEN the CI freshness gate runs
- THEN `git diff --exit-code -- output/` SHALL exit zero
- AND the CI step SHALL pass

#### Scenario: Committed output is stale

- GIVEN a generator was changed or data was updated without regenerating `output/`
- WHEN the CI freshness gate runs
- THEN `git diff --exit-code -- output/` SHALL exit non-zero
- AND the CI build SHALL fail with a message indicating which output files differ

#### Scenario: Freshness gate runs after generation

- GIVEN the CI workflow is executing
- WHEN the freshness step is reached
- THEN `python -m generators.cli generate` SHALL be invoked before `git diff`
- AND the diff MUST compare freshly generated content against the committed tree

## ADDED Requirements

### Requirement: CI Data Validation via CLI

The CI workflow MUST validate `data/*.json` against `schemas/` by invoking the
generator CLI (`python -m generators.cli validate`), which delegates to
`generators.validate.main()` and exits with its return code. The build MUST fail
if validation reports any schema error.

#### Scenario: CI validation passes

- GIVEN all data files satisfy their schemas
- WHEN the CI validation step runs `python -m generators.cli validate`
- THEN the step SHALL exit zero

#### Scenario: CI validation fails

- GIVEN a data file violates its schema
- WHEN the CI validation step runs `python -m generators.cli validate`
- THEN the step SHALL exit non-zero and the CI build SHALL fail
