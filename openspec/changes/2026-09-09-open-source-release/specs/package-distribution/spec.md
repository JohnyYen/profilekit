# Package Distribution Specification

## Purpose

Defines what makes this repository an installable, publishable Python package:
legal identity, `pyproject.toml` metadata, a non-colliding package name, and
packaged non-code assets. This is the entry point for a third party who runs
`pip install`.

## Requirements

### Requirement: Legal and community files present

The repository root MUST contain `LICENSE`, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SECURITY.md`, and `CHANGELOG.md`. `LICENSE` MUST state
an OSI-approved license and MUST NOT be a placeholder or a vendored skill's
license file.

#### Scenario: Root legal files present

- GIVEN the repository root
- WHEN it is listed
- THEN `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and
  `CHANGELOG.md` SHALL all be present
- AND `LICENSE` SHALL name a recognized OSI license

### Requirement: Publishable package metadata

`pyproject.toml` MUST declare non-empty `description`, `readme`, `license`,
`authors`, `keywords`, `classifiers`, and `[project.urls]` fields.

#### Scenario: Metadata is complete

- GIVEN `pyproject.toml`
- WHEN it is parsed as a PEP 621 project
- THEN `description`, `readme`, `license`, `authors`, `keywords`,
  `classifiers`, and `project.urls` SHALL all be present and non-empty

### Requirement: Non-colliding top-level package name

The distributed top-level Python package MUST NOT be named `generators`. It
MUST use a project-specific name that does not collide with a common PyPI
import namespace.

#### Scenario: Package importable under its new name

- GIVEN the package is installed
- WHEN a consumer imports it
- THEN the import path SHALL use the renamed, project-specific package name
- AND no top-level module named `generators` SHALL be shipped

### Requirement: Packaged non-code assets

The built sdist and wheel MUST include `py.typed` and the JSON Schema files
under `schemas/`, declared via `MANIFEST.in` and packaging configuration.

#### Scenario: Installed package finds its own schemas

- GIVEN the package is installed via `pip install` outside any git checkout
- WHEN a generator or validator resolves its schema files
- THEN it SHALL locate them from installed package data, not from a
  `__file__`-relative repository path

### Requirement: Tag-gated PyPI release

A release to PyPI MUST occur only in response to an explicit version tag
push, MUST be preceded by a dry-run publish to TestPyPI, and MUST NOT occur
on an ordinary push to `main`.

#### Scenario: Tag triggers release

- GIVEN a version tag (e.g. `v1.0.0`) is pushed
- WHEN the release workflow runs
- THEN it SHALL build and publish the package to PyPI

#### Scenario: Push to main does not release

- GIVEN a commit is pushed to `main` without a tag
- WHEN CI evaluates workflows
- THEN no PyPI publish SHALL occur
