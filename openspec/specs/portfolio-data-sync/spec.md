# Portfolio Data Sync Specification

## Purpose

Defines the contract for `generators/generate_portfolio_data.py`, which materializes
canonical `data/*.json` into the Next.js portfolio app's consumed JSON shapes under
`apps/portfolio/app/data/`. This is a distinct capability from `portfolio-generation`
(which writes `output/portfolio.md`); unlike that generator, this one legitimately
writes outside `output/` and into the app tree. The `portfolio-generation` output-only
rule is NOT violated — both generators coexist with non-overlapping output paths.

## Requirements

### Requirement: Canonical data is the source of truth for the portfolio

The system SHALL derive `apps/portfolio/app/data/{about,social,skills,projects}.json`
exclusively from canonical `data/*.json`. The app MUST NOT maintain hand-authored copies
of profile data. After the generator runs, the files under `apps/portfolio/app/data/`
MUST reflect the current state of canonical `data/`.

#### Scenario: Generator writes all four app data files

- GIVEN canonical `data/about.json`, `data/social.json`, `data/skills.json`, and
  `data/projects.json` are valid
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/about.json`, `apps/portfolio/app/data/social.json`,
  `apps/portfolio/app/data/skills.json`, and `apps/portfolio/app/data/projects.json`
  SHALL be created or overwritten with canonical-derived content
- AND no other file paths SHALL be written by this generator

#### Scenario: App data matches canonical source after regeneration

- GIVEN canonical `data/about.json` has been updated with a new field value
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/about.json` SHALL reflect the updated value

---

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
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/skills.json` SHALL contain the same N categories
  in source order, with all M details preserved per category

---

### Requirement: About and social fields map to app-consumed shapes

The generated `apps/portfolio/app/data/about.json` and
`apps/portfolio/app/data/social.json` MUST carry the fields the portfolio app
consumes, sourced from canonical `data/about.json` and `data/social.json`. No
divergent hand-authored copy of these values SHALL exist in the app tree.

#### Scenario: About fields present in generated file

- GIVEN `data/about.json` contains `name`, `title`, and `summary` fields
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/about.json` SHALL include those fields with identical values

#### Scenario: Social fields present in generated file

- GIVEN `data/social.json` contains platform URLs consumed by the portfolio
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/social.json` SHALL include those URLs

---

### Requirement: Projects fallback matches app GitHub-fallback contract

The generated `apps/portfolio/app/data/projects.json` MUST match the shape the
portfolio app expects when the live GitHub API fetch fails (the fallback contract).
Live GitHub fetch remains the primary source of project data and MUST NOT be
removed or altered. The generator provides the committed fallback only.

#### Scenario: Generated projects file satisfies fallback contract shape

- GIVEN `data/projects.json` contains valid project entries
- WHEN `generate_portfolio_data.py` is executed
- THEN `apps/portfolio/app/data/projects.json` SHALL contain entries that conform
  to the app's GitHub-fallback shape (required fields: `name`, `description`, `url`,
  `language`, `topics`)
- AND extra canonical fields not required by the fallback contract SHALL be harmlessly ignored

#### Scenario: Live GitHub fetch takes precedence over fallback

- GIVEN `apps/portfolio/app/data/projects.json` contains generated fallback data
- WHEN the portfolio app loads and the GitHub API responds successfully
- THEN the app SHALL display live GitHub data, not the fallback data

---

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

---

### Requirement: Generator integrates into generate_all and is golden-tested

`generate_portfolio_data.py` MUST be registered in `generate_all` so it executes
as part of the standard pipeline run. It MUST be covered by golden/unit tests
(RED-GREEN-REFACTOR). The generated app data files MUST be committed to the
repository as artifacts (equivalent treatment to `output/`).

#### Scenario: generate_all includes portfolio data sync step

- GIVEN `generate_all` is invoked
- WHEN the run completes
- THEN `apps/portfolio/app/data/*.json` SHALL have been written by the pipeline
- AND the portfolio data sync step SHALL appear in the run log

#### Scenario: Golden tests validate transform output

- GIVEN a known set of canonical input fixtures
- WHEN the test suite runs
- THEN golden files for each of the four generated app data files SHALL match byte-for-byte
- AND any deviation SHALL cause the test to fail with a diff

#### Scenario: Generator fails fast on missing canonical input

- GIVEN one of the required canonical source files is absent
- WHEN `generate_portfolio_data.py` is executed
- THEN it SHALL exit with a non-zero status code and a descriptive error message
- AND no partial output files SHALL be silently left in `apps/portfolio/app/data/`

---

### Requirement: Output path non-conflict with portfolio-generation capability

`generate_portfolio_data.py` writes exclusively to `apps/portfolio/app/data/`
and MUST NOT write to `output/`. The existing `portfolio-generation` capability
(`generate_portfolio.py`) writes exclusively to `output/` and MUST NOT be modified
by this change. Both generators MUST coexist without output path overlap.

#### Scenario: Separate generators write to non-overlapping paths

- GIVEN both `generate_portfolio.py` and `generate_portfolio_data.py` are executed
- WHEN each completes
- THEN `generate_portfolio.py` SHALL have written only to `output/`
- AND `generate_portfolio_data.py` SHALL have written only to `apps/portfolio/app/data/`
- AND no file SHALL be written to both paths by either generator
