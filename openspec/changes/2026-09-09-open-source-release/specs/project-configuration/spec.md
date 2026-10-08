# Project Configuration Specification

## Purpose

Defines how the installed tool locates a user's project — data, output, and
configuration — from the working directory rather than from its own
installation path, plus `profile.toml`, `profile init` scaffolding,
externalized generator opinions, and git-optional operation.

## Requirements

### Requirement: CWD-based project discovery

The tool MUST resolve `data_dir`, `output_dir`, and `schemas_dir` relative to
the current working directory or an explicit `profile.toml`, and MUST NOT
derive them from the installed package's own file location.

#### Scenario: Discovery from an installed package

- GIVEN the package is installed via `pip install` and the user runs a
  command from their own project directory
- WHEN the tool resolves its data and output directories
- THEN it SHALL resolve them relative to the current working directory or
  `profile.toml`
- AND it SHALL NOT read or write inside site-packages

#### Scenario: No config file present

- GIVEN no `profile.toml` exists in the current directory or any parent
- WHEN a command needing project paths runs
- THEN the tool SHALL fall back to documented default relative paths under
  the current working directory

### Requirement: profile.toml declares project paths

A `profile.toml` at the project root MAY declare `data_dir`, `output_dir`,
`schemas_dir`, and generator-specific overrides. When present, its values
MUST take precedence over defaults.

#### Scenario: profile.toml overrides the default output directory

- GIVEN `profile.toml` declares a custom `output_dir`
- WHEN any generator runs
- THEN artifacts SHALL be written under that configured `output_dir`

### Requirement: profile init scaffolds a new project

`profile init` MUST create a minimal valid project in the current directory:
`profile.toml` and an example `data/` tree conforming to the packaged
schemas, with no reference to the maintainer's own identity or data.

#### Scenario: Init in an empty directory

- GIVEN an empty directory
- WHEN `profile init` runs
- THEN it SHALL create `profile.toml` and an example `data/` tree
- AND none of the created files SHALL contain the maintainer's name, email,
  or handle

### Requirement: Externalized generator opinions

Presentation choices currently hardcoded in generators (greeting text,
about-block image, footer text, RenderCV theme/locale, schema version pin)
MUST be configurable via `profile.toml` or data files, with today's values
preserved as defaults.

#### Scenario: Overriding a hardcoded opinion

- GIVEN `profile.toml` sets a custom greeting template
- WHEN `generate_github_readme` runs
- THEN the rendered greeting SHALL use the configured template

#### Scenario: Default behavior unchanged when not configured

- GIVEN `profile.toml` sets no override
- WHEN any generator with an externalized opinion runs
- THEN it SHALL reproduce today's default text exactly

### Requirement: profile check degrades without git

`profile check` MUST run to completion outside a git repository.
Git-dependent checks MUST be skipped with a clear message, not raise an
error, when `.git` is absent.

#### Scenario: Check outside a git repository

- GIVEN the current directory is not a git checkout
- WHEN `profile check` runs
- THEN it SHALL complete without error
- AND it SHALL report the git-dependent check as skipped, not failed

#### Scenario: Check inside a git repository

- GIVEN the current directory is a git checkout with a clean working tree
- WHEN `profile check` runs
- THEN the git-cleanliness check SHALL run and pass as before
