# Delta for portfolio-data-sync

## MODIFIED Requirements

### Requirement: Canonical data is the source of truth for the portfolio destination

The system SHALL derive the portfolio app's consumed JSON shapes exclusively
from canonical `data/*.json`, and SHALL write them to a configurable
destination path (defaulting to `apps/portfolio/app/data/`) declared as a
`publisher` destination in `profile.toml`. The app MUST NOT maintain
hand-authored copies of profile data. After the publisher runs, the files
under the configured destination MUST reflect the current state of
canonical `data/`.
(Previously: this component wrote to a hardcoded, non-overridable path and
was classified as a generator, not a publisher)

#### Scenario: Publisher writes all four app data files

- GIVEN canonical `data/about.json`, `data/social.json`, `data/skills.json`,
  and `data/projects.json` are valid
- WHEN the `portfolio_data` publisher runs
- THEN `about.json`, `social.json`, `skills.json`, and `projects.json` SHALL
  be created or overwritten at the configured destination
- AND no other file paths SHALL be written by this publisher

#### Scenario: App data matches canonical source after regeneration

- GIVEN canonical `data/about.json` has been updated with a new field value
- WHEN the `portfolio_data` publisher runs
- THEN the destination's `about.json` SHALL reflect the updated value

#### Scenario: Destination path is configurable

- GIVEN `profile.toml` declares a custom destination path for
  `portfolio_data`
- WHEN the publisher runs
- THEN it SHALL write to the configured path, not the default
  `apps/portfolio/app/data/`

### Requirement: Publisher is registered in the single component registry and is golden-tested

`portfolio_data` MUST be registered in the single component registry as a
`publisher`-kind component of kind `filesystem`, and MUST be invoked by
`profile publish` — never by `profile generate`, which invokes only
`generator`-kind components. It MUST be covered by golden/unit tests
(RED-GREEN-REFACTOR). The generated app data files MUST be committed to the
repository as artifacts.
(Previously: registered only in `generate_all.py`'s internal list, absent
from `cli.py`'s `GENERATORS` dict, which caused `profile generate all` to
skip it while direct `generate_all` invocation did not — the shipped
divergence bug)

#### Scenario: profile publish invokes the portfolio data sync

- GIVEN `portfolio_data` is registered as a `publisher`-kind component
- WHEN `profile publish all` runs
- THEN `apps/portfolio/app/data/*.json` (or the configured destination)
  SHALL have been written
- AND the portfolio data sync step SHALL appear in the run log

#### Scenario: profile generate does not write app data

- GIVEN `portfolio_data` is registered as a `publisher`-kind component
- WHEN `profile generate all` runs
- THEN it SHALL NOT invoke `portfolio_data`
- AND no file outside the configured `output_dir` SHALL be written

#### Scenario: App data freshness stays gated by profile check

- GIVEN committed `apps/portfolio/app/data/*.json` differs from what
  `portfolio_data` would write for the current canonical data
- WHEN `profile check` runs
- THEN it SHALL run `publish --dry-run` for `filesystem`-kind destinations
- AND it SHALL exit non-zero reporting the stale destination

#### Scenario: Regression — divergence bug does not recur

- GIVEN the single component registry is the only enumeration source for
  every command that resolves components
- WHEN `profile publish all` and any standalone publish entry point are
  invoked against the same data
- THEN both SHALL produce identical `apps/portfolio/app/data/*.json` output
- AND neither invocation path SHALL omit `portfolio_data`

#### Scenario: Golden tests validate transform output

- GIVEN a known set of canonical input fixtures
- WHEN the test suite runs
- THEN golden files for each of the four generated app data files SHALL
  match byte-for-byte
- AND any deviation SHALL cause the test to fail with a diff
