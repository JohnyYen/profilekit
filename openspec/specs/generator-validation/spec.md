# Generator Validation Specification

## Purpose

Defines the contract for schema-authoritative data validation and build-time icon
reachability checks. `validate.py` MUST enforce `schemas/*.schema.json` via the
`jsonschema` library, and unresolvable icon references MUST produce non-fatal
build-time warnings.

## Requirements

### Requirement: Schema-Authoritative Validation

`validate.py` MUST validate each data file against its corresponding JSON Schema
using the `jsonschema` library. Validation MUST enforce types, required fields,
and complex shapes including object properties and `oneOf` variants (e.g.,
string-or-object skill entries). Each file MUST produce a per-file PASS or FAIL
result. Any validation failure MUST cause a non-zero exit code. The existing
cross-field `portfolioHighlights` warning (via `validate_portfolio_highlights`)
MUST be preserved.

#### Scenario: Valid data files

- GIVEN all `data/*.json` files conform to their schemas
- WHEN `validate.py` runs
- THEN each file SHALL report PASS
- AND the process SHALL exit zero

#### Scenario: Type violation

- GIVEN a data file contains a field with an incorrect type (e.g., a string where
  an array is required)
- WHEN `validate.py` runs
- THEN the file SHALL report FAIL with a message identifying the file and the
  offending field
- AND the process SHALL exit non-zero

#### Scenario: Missing required field

- GIVEN a data file omits a field listed in the schema's `required` array
- WHEN `validate.py` runs
- THEN the file SHALL report FAIL identifying the file and the missing field
- AND the process SHALL exit non-zero

#### Scenario: oneOf shape violation

- GIVEN a data file contains a skill entry that satisfies neither branch of a
  `oneOf` (neither plain string nor the object variant with required keys)
- WHEN `validate.py` runs
- THEN the file SHALL report FAIL identifying the file and the invalid entry
- AND the process SHALL exit non-zero

#### Scenario: portfolioHighlights cross-field warning preserved

- GIVEN `about.portfolioHighlights` references a project name absent from
  `data/projects.json`
- WHEN `validate.py` runs
- THEN a cross-field warning SHALL be emitted identifying the unmatched name
- AND the warning SHALL NOT cause a non-zero exit on its own

### Requirement: Icon Reachability Check

A build-time check MUST warn when a configured skillicons slug or `iconUrl` does
not resolve to a reachable resource. The warning MUST be non-fatal so that CI
does not become flaky. The check MUST be skippable or offline-safe via a flag or
environment variable so it can be disabled in offline or restricted network
environments.

#### Scenario: All icons reachable

- GIVEN all skillicons slugs and `iconUrl` values resolve successfully
- WHEN the icon reachability check runs
- THEN no warnings SHALL be emitted
- AND the process SHALL exit zero

#### Scenario: Unresolvable slug

- GIVEN a skillicons slug configured in `data/skills.json` does not resolve
- WHEN the icon reachability check runs
- THEN a warning SHALL be emitted identifying the slug and its context
- AND the process SHALL still exit zero (non-fatal)

#### Scenario: Unresolvable iconUrl

- GIVEN an `iconUrl` entry does not resolve (HTTP 4xx/5xx or network error)
- WHEN the icon reachability check runs
- THEN a warning SHALL be emitted identifying the URL and its context
- AND the process SHALL still exit zero (non-fatal)

#### Scenario: Offline / skip mode

- GIVEN the icon check is disabled via the designated opt-out flag or environment
  variable
- WHEN `validate.py` or the icon check helper runs
- THEN the icon reachability step SHALL be skipped entirely
- AND no network requests SHALL be made
- AND the process SHALL exit zero

### Requirement: URL Link Validation

A link-validation checker MUST validate URLs present in `projects.json` and
`social.json`. The checker MUST warn on empty or unreachable URLs and MUST
NOT fail the build (warn-only, non-fatal). The checker MUST be skippable via
the `SKIP_LINK_CHECK=1` environment variable and MUST be safe to run in offline
environments (no network request is made when skipped). The checker MUST mirror
the warn-only, skippable pattern established by the icon reachability check
(`generators/icons.py`).

#### Scenario: All URLs reachable

- GIVEN all URLs in `projects.json` and `social.json` return a successful HTTP response
- WHEN the link validation check runs
- THEN no warnings SHALL be emitted
- AND the process SHALL exit zero

#### Scenario: Empty URL field

- GIVEN a field in `projects.json` or `social.json` contains an empty string URL
- WHEN the link validation check runs
- THEN a warning SHALL be emitted identifying the field and its context
- AND the process SHALL still exit zero (non-fatal)

#### Scenario: Unreachable URL

- GIVEN a URL in `projects.json` or `social.json` returns an HTTP 4xx/5xx response or a network error
- WHEN the link validation check runs
- THEN a warning SHALL be emitted identifying the URL and its context
- AND the process SHALL still exit zero (non-fatal)

#### Scenario: Skip via environment variable

- GIVEN the `SKIP_LINK_CHECK=1` environment variable is set
- WHEN the link validation check is invoked
- THEN the check SHALL be skipped entirely
- AND no network requests SHALL be made
- AND the process SHALL exit zero

#### Scenario: Offline CI environment

- GIVEN the CI environment sets `SKIP_LINK_CHECK=1` to avoid network dependency
- WHEN the CI validation step runs
- THEN the link check SHALL not block the build
- AND all other validation steps SHALL proceed normally
