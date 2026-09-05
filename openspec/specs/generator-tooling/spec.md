# Generator Tooling Specification

## Purpose

Defines the contract for CI test execution and generator runnability. Covers the
pytest integration in CI and the `generate_all.py` dual-invocation requirement.

## Requirements

### Requirement: CI Runs Pytest Suite

The CI workflow MUST install Python dependencies (including `pytest` and
`jsonschema`) and execute the full `pytest` suite as part of every build. The
build MUST fail with a non-zero exit code if any test fails. The validate step
MUST NOT be the sole CI quality gate.

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
- THEN dependencies SHALL be installed before `pytest` is invoked
- AND `pytest` SHALL have access to `jsonschema` and all generator imports

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
