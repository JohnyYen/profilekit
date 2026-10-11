# Delta for generator-tooling

## MODIFIED Requirements

### Requirement: Pre-commit Hooks

The repository MUST provide a `.pre-commit-config.yaml` that runs at minimum
ruff format and ruff check (and optionally fast validation/test subsets)
before each commit. The `pre-commit` package MUST be included as a dev
dependency. Hooks MUST run via each tool's own self-contained hook
environment and MUST NOT require the contributor to have `uv` installed on
their machine. Developer setup MUST be documented with a `pre-commit
install` step.
(Previously: hooks were invoked via `uv run`, requiring `uv` to be installed
locally even for contributors who use plain `pip`)

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

## ADDED Requirements

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
