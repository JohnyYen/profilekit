# Generator Robustness Specification

## Purpose

Defines the contract for generator error handling, platform-variant data
consumption, shared formatting helpers, and golden/snapshot test coverage.
Together these requirements eliminate raw tracebacks, dead data, duplicated
formatting logic, and untested output drift.

## Requirements

### Requirement: Graceful Generator Error Handling

Each generator MUST handle the following error conditions without emitting a raw
Python traceback: missing input file, malformed JSON, and missing required field.
In each case the generator MUST emit a clear human-readable message that
identifies the file and the field (where applicable) and MUST exit with a
non-zero exit code. Unexpected errors (outside these known categories) MUST NOT
be swallowed and MUST propagate normally.

#### Scenario: Missing input file

- GIVEN a required data file (e.g., `data/about.json`) does not exist
- WHEN a generator runs
- THEN the generator SHALL emit a message identifying the missing file path
- AND the process SHALL exit non-zero
- AND no Python traceback SHALL appear in standard output or standard error

#### Scenario: Malformed JSON

- GIVEN a data file contains invalid JSON
- WHEN a generator reads that file
- THEN the generator SHALL emit a message identifying the file and the parse
  error location
- AND the process SHALL exit non-zero
- AND no Python traceback SHALL appear

#### Scenario: Missing required field

- GIVEN a data file is valid JSON but omits a field the generator requires
- WHEN the generator accesses that field
- THEN the generator SHALL emit a message identifying the file and the missing
  field name
- AND the process SHALL exit non-zero
- AND no Python traceback SHALL appear

#### Scenario: Unexpected error propagates

- GIVEN an unexpected runtime error occurs (e.g., an unhandled exception outside
  known I/O or parse categories)
- WHEN a generator runs
- THEN the error MUST NOT be silently caught or swallowed
- AND the process SHALL exit non-zero

### Requirement: whatIBuildVariants Platform Wiring

Each generator MUST read `about.whatIBuildVariants[<platform>]` when that key is
present and non-null, using it in place of `about.whatIBuild`. When the
platform-specific variant is absent or null, the generator MUST fall back to
`about.whatIBuild`. This behavior MUST be backward-compatible: existing data
without `whatIBuildVariants` MUST render identically to before this change.

Platform keys are: `github`, `linkedin`, `cv`, `portfolio`.

#### Scenario: Platform variant present

- GIVEN `about.whatIBuildVariants` contains a non-null entry for the generator's
  platform key
- WHEN that generator runs
- THEN the output SHALL use the platform-specific variant value for the
  "what I build" text

#### Scenario: Platform variant absent, fallback to whatIBuild

- GIVEN `about.whatIBuildVariants` is absent, null, or does not contain the
  generator's platform key
- WHEN that generator runs
- THEN the output SHALL use `about.whatIBuild` exactly as before this change

#### Scenario: Backward compatibility

- GIVEN `about.json` does not include the `whatIBuildVariants` field at all
- WHEN all generators run
- THEN every generator SHALL produce output byte-identical to its pre-change
  output for the same data

### Requirement: Shared Formatting Helpers

Experience, education, and date formatting logic MUST be provided by shared,
reusable helper functions used across all generators that need them (`generate_cv.py`,
`generate_linkedin.py`, `generate_github_readme.py`). No generator SHALL
duplicate formatting logic already provided by a shared helper. Existing output
artifacts MUST remain byte-stable for current data (regression invariant).

#### Scenario: Consistent date formatting across generators

- GIVEN the same experience entry is rendered by both the CV and LinkedIn
  generators
- WHEN both generators run on identical input data
- THEN both SHALL produce the same date string for that entry
- AND both SHALL use the same shared helper to produce it

#### Scenario: No duplicated formatter code

- GIVEN shared helpers exist in the designated utility module
- WHEN any generator formats an experience, education, or date value
- THEN it SHALL call the shared helper rather than implementing equivalent logic
  inline

#### Scenario: Byte-stable output after deduplication

- GIVEN golden snapshots were captured before the deduplication refactor
- WHEN generators run after the refactor with the same input data
- THEN all output artifacts SHALL be byte-identical to the pre-refactor golden
  snapshots

### Requirement: Golden Snapshot Tests

Full-output golden/snapshot tests MUST exist for each generator's output
artifact. Each golden test MUST compare the complete content of the generated
file against a committed reference snapshot. The test suite MUST fail if any
generator's output deviates from its snapshot. Golden snapshots MUST be
committed before the shared-formatter deduplication refactor begins.

#### Scenario: Output matches snapshot

- GIVEN a committed golden snapshot exists for a generator's output file
- WHEN the generator runs on the canonical data set
- THEN the produced file content SHALL be byte-identical to the snapshot
- AND the test SHALL pass

#### Scenario: Output deviates from snapshot

- GIVEN a committed golden snapshot exists
- WHEN a generator produces output that differs from the snapshot
- THEN the golden test SHALL fail
- AND the diff SHALL be visible in test output

#### Scenario: Snapshots committed before refactor

- GIVEN the shared-formatter deduplication refactor has not yet been applied
- WHEN golden tests are first established
- THEN snapshots SHALL be committed to the repository at that point
- AND subsequent refactor steps SHALL be gated on these snapshots remaining green
