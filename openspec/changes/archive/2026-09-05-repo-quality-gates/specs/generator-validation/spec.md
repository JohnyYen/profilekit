# Delta for Generator Validation

## ADDED Requirements

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
