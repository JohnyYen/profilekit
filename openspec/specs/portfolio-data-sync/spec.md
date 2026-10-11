# Portfolio Data Sync Specification

## Purpose

Defines the contract for the `portfolio_data` publisher, which materializes
canonical `data/*.json` into the Next.js portfolio app's consumed JSON shapes under
`apps/portfolio/app/data/`. This is a distinct capability from `portfolio-generation`
(which writes `output/portfolio.md`). The publisher is registered as a `filesystem`-kind
publisher and is invoked by `profile publish`, not by `profile generate`.

## Requirements

### Requirement: Canonical data is the source of truth for the portfolio destination

The system SHALL derive the portfolio app's consumed JSON shapes exclusively
from canonical `data/*.json`, and SHALL write them to a configurable
destination path (defaulting to `apps/portfolio/app/data/`) declared as a
`publisher` destination in `profile.toml`. The app MUST NOT maintain
hand-authored copies of profile data. After the publisher runs, the files
under the configured destination MUST reflect the current state of
canonical `data/`.

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
**publisher** — the entry-point group that decides which command may reach it —
declaring the **kind** `filesystem`, which selects its implementation. The two
words name different axes and are easy to conflate. It MUST be invoked by
`profile publish` — never by `profile generate`, which invokes only
`generator`-kind components. It MUST be covered by golden/unit tests
(RED-GREEN-REFACTOR). The generated app data files MUST be committed to the
repository as artifacts. Registration is an entry point declared in
`pyproject.toml`; the registry is the only enumeration source.

> Merged during review of the archive. Two requirements stated the same
> registration rule — one from the delta spec, one from the base — which left
> the capability asserting it twice and in slightly different words.

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

#### Scenario: Registry discovers the portfolio_data publisher

- GIVEN the component registry is queried for publisher entry points
- WHEN the query completes
- THEN `portfolio_data` SHALL be enumerated as a registered publisher
- AND it SHALL NOT appear in the generator list

#### Scenario: Publisher fails fast on missing canonical input

- GIVEN one of the required canonical source files is absent
- WHEN the publisher runs
- THEN it SHALL exit with a non-zero status code and a descriptive error
  message
- AND no partial output files SHALL be left in the configured destination

> Restored during review of the archive merge. This was the capability's only
> failure-path scenario and the merge dropped it, leaving the requirement
> asserting registration and golden coverage but nothing about behaviour on
> bad input. The wording is updated from the original — which named
> `generate_portfolio_data.py` and a hardcoded destination — to the publisher
> and its configured destination.

### Requirement: Skills passthrough preserves canonical shape

The generated `apps/portfolio/app/data/skills.json` MUST carry the canonical
`{categories: [{label, details}]}` shape without lossy bucket mapping. Each `details`
entry MAY be a plain string or an object `{name, icon?, iconUrl?}`. The portfolio's
`SkillsSection` component MUST render canonical categories directly: display `label`
as the category heading; for each detail, render an icon when `icon` or `iconUrl` is
present, and plain text otherwise.

#### Scenario: Skills with icon objects render with icon indicator

- GIVEN `data/skills.json` contains a category with a detail `{name: "React", icon: "react"}`
- WHEN the generator runs and `SkillsSection` renders the output
- THEN the skill SHALL be rendered with its icon (or icon URL) alongside the name

#### Scenario: Skills with plain string details render as text

- GIVEN `data/skills.json` contains a category with a detail `"TypeScript"` (string)
- WHEN the generator runs and `SkillsSection` renders the output
- THEN the skill SHALL be rendered as plain text without an icon

#### Scenario: Generated skills file preserves category structure

- GIVEN `data/skills.json` has N categories each with M details
- WHEN `portfolio_data` is executed
- THEN `apps/portfolio/app/data/skills.json` SHALL contain the same N categories
  in source order, with all M details preserved per category

### Requirement: About and social fields map to app-consumed shapes

The generated `apps/portfolio/app/data/about.json` and
`apps/portfolio/app/data/social.json` MUST carry the fields the portfolio app
consumes, sourced from canonical `data/about.json` and `data/social.json`. No
divergent hand-authored copy of these values SHALL exist in the app tree.

#### Scenario: About fields present in generated file

- GIVEN `data/about.json` contains `name`, `title`, and `summary` fields
- WHEN `portfolio_data` is executed
- THEN `apps/portfolio/app/data/about.json` SHALL include those fields with identical values

#### Scenario: Social fields present in generated file

- GIVEN `data/social.json` contains platform URLs consumed by the portfolio
- WHEN `portfolio_data` is executed
- THEN `apps/portfolio/app/data/social.json` SHALL include those URLs

### Requirement: Projects fallback matches app GitHub-fallback contract

The generated `apps/portfolio/app/data/projects.json` MUST match the shape the
portfolio app expects when the live GitHub API fetch fails (the fallback contract).
Live GitHub fetch remains the primary source of project data and MUST NOT be
removed or altered. The generator provides the committed fallback only.

#### Scenario: Generated projects file satisfies fallback contract shape

- GIVEN `data/projects.json` contains valid project entries
- WHEN `portfolio_data` is executed
- THEN `apps/portfolio/app/data/projects.json` SHALL contain entries that conform
  to the app's GitHub-fallback shape (required fields: `name`, `description`, `url`,
  `language`, `topics`)
- AND extra canonical fields not required by the fallback contract SHALL be harmlessly ignored

#### Scenario: Live GitHub fetch takes precedence over fallback

- GIVEN `apps/portfolio/app/data/projects.json` contains generated fallback data
- WHEN the portfolio app loads and the GitHub API responds successfully
- THEN the app SHALL display live GitHub data, not the fallback data

### Requirement: Layout metadata and CvSection source from canonical data

`apps/portfolio/app/layout.tsx` metadata (page title, author, description, JSON-LD
`Person` name, url, sameAs) and `CvSection` CV title MUST be sourced from canonical
`data/about.json` and `data/social.json`. Values absent from canonical (CV file size,
CV date) SHALL be derived programmatically or defined as a documented constant;
they MUST NOT be fabricated or hard-coded as silent assumptions.

#### Scenario: Layout title matches canonical name

- GIVEN `data/about.json` contains `name: "Jane Doe"`
- WHEN the portfolio app renders `layout.tsx`
- THEN the HTML `<title>` and JSON-LD `Person.name` SHALL include "Jane Doe"

#### Scenario: JSON-LD sameAs includes canonical social URLs

- GIVEN `data/social.json` contains profile URLs for GitHub and LinkedIn
- WHEN the portfolio app renders `layout.tsx`
- THEN the JSON-LD `Person.sameAs` array SHALL include those URLs

#### Scenario: CV title in CvSection matches canonical value

- GIVEN `data/about.json` carries a CV title field
- WHEN `CvSection` renders
- THEN the displayed CV title SHALL match the canonical value

#### Scenario: Non-canonical CV metadata uses documented constant

- GIVEN CV file size or date is not present in canonical data
- WHEN `CvSection` renders
- THEN the value SHALL come from a documented constant or derivation, not a silent fabrication
