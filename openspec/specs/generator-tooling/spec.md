# Generator Tooling Specification

## Purpose

Defines the contract for CI test execution and generator runnability. Covers the
pytest integration in CI and the `generate_all.py` dual-invocation requirement.

## Requirements

### Requirement: CI Runs Pytest Suite

The CI workflow MUST install Python dependencies (including `pytest`,
`jsonschema`, `pytest-cov`, and all dev dependencies) and execute the full
`pytest` suite as part of every build. The build MUST fail with a non-zero exit
code if any test fails. The validate step MUST NOT be the sole CI quality gate.
The pytest invocation MUST include coverage measurement.
(Previously: did not include pytest-cov or dev dependencies in the install requirement)

#### Scenario: Passing test suite

- GIVEN all tests pass
- WHEN the CI workflow runs
- THEN the build SHALL succeed
- AND test results SHALL be reported in CI output

#### Scenario: Failing test suite

- GIVEN at least one test fails
- WHEN the CI workflow runs
- THEN the build SHALL fail with a non-zero exit code
- AND the failing test name(s) SHALL appear in CI output

#### Scenario: Dependency installation precedes test run

- GIVEN a clean CI environment with no pre-installed dependencies
- WHEN the CI workflow starts
- THEN dependencies SHALL be installed (including dev extras) before `pytest` is invoked
- AND `pytest` SHALL have access to `jsonschema`, `pytest-cov`, and all generator imports

### Requirement: generate_all.py Dual Invocation

`generators/generate_all.py` MUST run successfully both as a plain script
(`python generators/generate_all.py`) and as a module (`python -m
generators.generate_all`). Both invocation modes MUST produce identical output
artifacts under `output/` and MUST exit zero on success.

#### Scenario: Script invocation

- GIVEN all data files are valid
- WHEN `python generators/generate_all.py` is executed from the repository root
- THEN all output artifacts SHALL be written to `output/`
- AND the process SHALL exit zero

#### Scenario: Module invocation

- GIVEN all data files are valid
- WHEN `python -m generators.generate_all` is executed from the repository root
- THEN all output artifacts SHALL be written to `output/`
- AND the process SHALL exit zero
- AND the output SHALL be byte-identical to the script invocation result

#### Scenario: Invocation failure propagates

- GIVEN any generator encounters an error during a full run
- WHEN either invocation mode is used
- THEN `generate_all.py` SHALL exit non-zero
- AND the error message SHALL identify which generator failed

### Requirement: Output Freshness Gate

The CI workflow MUST regenerate all output artifacts by running `python -m
generators.generate_all` and then MUST fail the build with a non-zero exit code
if the committed `output/` directory differs from the freshly generated output
(verified via `git diff --exit-code -- output/`).

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
- THEN `python -m generators.generate_all` SHALL be invoked before `git diff`
- AND the diff MUST compare freshly generated content against the committed tree

### Requirement: Lint and Format (Ruff)

The project MUST pass `ruff check` (lint) and `ruff format --check` (format)
with configuration defined in `pyproject.toml`. The CI workflow MUST run both
checks and fail the build if either reports violations. The `generators/` and
`tests/` directories MUST be covered by the ruff configuration.

#### Scenario: No lint violations

- GIVEN all source files conform to the configured ruff rules
- WHEN `ruff check` runs
- THEN no violations SHALL be reported
- AND the CI step SHALL exit zero

#### Scenario: Lint violation detected

- GIVEN a source file contains a rule violation (e.g., unused import)
- WHEN `ruff check` runs
- THEN the offending file, line, and rule SHALL be reported
- AND the CI step SHALL exit non-zero

#### Scenario: Format violation detected

- GIVEN a source file is not formatted according to ruff's style
- WHEN `ruff format --check` runs
- THEN the unformatted file(s) SHALL be reported
- AND the CI step SHALL exit non-zero

#### Scenario: Both checks pass

- GIVEN all source files are lint-clean and properly formatted
- WHEN both `ruff check` and `ruff format --check` run in CI
- THEN both SHALL exit zero
- AND the CI lint/format step SHALL be marked passing

### Requirement: Static Type Check (mypy)

The `generators/` package MUST pass mypy type checking in CI with pragmatic
strictness (configured in `pyproject.toml`). The CI workflow MUST run mypy
and fail the build if type errors are reported.

#### Scenario: No type errors

- GIVEN all generator source files are type-correct under the configured mypy settings
- WHEN the CI mypy step runs
- THEN mypy SHALL report zero errors
- AND the CI step SHALL exit zero

#### Scenario: Type error detected

- GIVEN a generator file introduces a type mismatch or missing annotation
- WHEN the CI mypy step runs
- THEN mypy SHALL report the file, line, and error message
- AND the CI step SHALL exit non-zero

### Requirement: Test Coverage Enforcement

The CI workflow MUST measure test coverage (via `pytest-cov`) and MUST fail
the build if measured coverage falls below a defined threshold. The threshold
MUST be set at or below the coverage measured at baseline so it passes on the
existing 113 tests without artificial inflation. The threshold value MUST be
recorded in `pyproject.toml`.

#### Scenario: Coverage at or above threshold

- GIVEN the test suite achieves coverage >= the configured threshold
- WHEN the CI coverage step runs
- THEN pytest-cov SHALL report the coverage percentage
- AND the CI step SHALL exit zero

#### Scenario: Coverage below threshold

- GIVEN code changes reduce coverage below the configured threshold
- WHEN the CI coverage step runs
- THEN pytest-cov SHALL report the measured percentage and the threshold
- AND the CI step SHALL exit non-zero, blocking the build

#### Scenario: Existing 113 tests remain green

- GIVEN no behavioral changes are made to generators or validators
- WHEN the full pytest suite runs under coverage measurement
- THEN all 113 existing tests SHALL pass
- AND coverage measurement SHALL not alter test outcomes

### Requirement: Pre-commit Hooks

The repository MUST provide a `.pre-commit-config.yaml` that runs at minimum
ruff format and ruff check (and optionally fast validation/test subsets) before
each commit. The `pre-commit` package MUST be included as a dev dependency. Hooks MUST run via each tool's own self-contained hook
environment and MUST NOT require the contributor to have `uv` installed on
their machine. Developer setup MUST be documented with a `pre-commit
install` step.

#### Scenario: Pre-commit hooks run on commit

- GIVEN a developer has run `pre-commit install`
- WHEN they attempt to commit source changes
- THEN the configured hooks SHALL execute automatically
- AND a hook failure SHALL abort the commit with an explanatory message

#### Scenario: Hooks run without uv installed

- GIVEN a contributor's machine has `pip` but not `uv` installed
- WHEN they run `pre-commit install` and then commit
- THEN the hooks SHALL execute successfully without requiring `uv`

#### Scenario: Format violation caught locally

- GIVEN a staged file is not formatted according to ruff
- WHEN pre-commit runs
- THEN the ruff-format hook SHALL either fix the file or report the
  violation
- AND the commit SHALL be blocked until the file is properly formatted

### Requirement: Test and fixture data neutrality

Tests and their fixtures MUST NOT contain the maintainer's real name, email,
phone number, or other real PII. Golden/snapshot tests MUST run against a
committed fictional test dataset, not the live `data/` directory. No test
MUST mutate the real `output/` tree, `apps/portfolio/app/data/`, or any
other tracked working-tree path; tests that exercise a full pipeline run
MUST write to an isolated temporary directory (`tmp_path`).

#### Scenario: No real PII in test fixtures

- GIVEN the test suite's fixtures and golden files
- WHEN they are scanned for the maintainer's name, email, and phone number
- THEN no match SHALL be found

#### Scenario: Golden tests use the fictional test dataset

- GIVEN the golden test suite
- WHEN it runs
- THEN it SHALL read from a committed fictional dataset, not the real
  `data/` directory

#### Scenario: Full pipeline test does not mutate the working tree

- GIVEN a test exercises the full generation pipeline
- WHEN it runs
- THEN all output SHALL be written under `tmp_path`
- AND the repository's tracked `output/` and `apps/portfolio/app/data/`
  SHALL remain unchanged after the test

### Requirement: Documentation surface for third-party adoption

The root `README.md` MUST present the project as an installable generation
tool, not as the maintainer's personal profile. A `docs/` directory MUST
exist documenting the public output data contract and providing authoring
guides for writing a new generator and a new publisher.

#### Scenario: README frames the tool for adopters

- GIVEN the root `README.md`
- WHEN a third party reads it
- THEN it SHALL describe installation, `profile init`, and
  `profile generate`/`profile publish` usage before any mention of the
  maintainer's personal data

#### Scenario: docs/ covers the contract and authoring

- GIVEN the `docs/` directory
- WHEN it is listed
- THEN it SHALL include the output data contract reference and a guide for
  authoring a generator and a publisher
