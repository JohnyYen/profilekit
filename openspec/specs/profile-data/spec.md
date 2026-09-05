# Delta Spec: profile-data — Platform-Specific Data Variety

Change: `add-platform-specific-data-variety`

This delta adds optional, backward-compatible platform-specific fields to the
`about.json` data model, extends its JSON Schema non-breakingly, and defines the
use-if-present-else-fallback behavior for each generator.

## ADDED Requirements

### Requirement: Optional platform-specific fields on about.json

The system SHALL support five new optional fields on `data/about.json`:
`githubReadmeSummary` (string), `linkedinHeadline` (string), `cvHeadline`
(string), `portfolioHighlights` (array of strings), and `whatIBuildVariants`
(object keyed by platform). All five fields MUST be optional and MUST NOT be
required for `about.json` to be valid. Their absence, or a `null` value, MUST be
treated as "not set" and MUST NOT change any existing behavior.

#### Scenario: New fields present with values

- **Given** an `about.json` that includes all five new fields with non-null
  values
- **When** the data is loaded by any consumer
- **Then** each field's value SHALL be available to the corresponding generator
- **And** the existing fields (`username`, `headline`, `tagline`, `description`,
  etc.) SHALL remain unchanged and available.

#### Scenario: New fields absent (backward compatibility)

- **Given** an existing `about.json` that does not declare any of the five new
  fields
- **When** the data is loaded and generators run
- **Then** the system SHALL behave exactly as it did before this change
- **And** no error SHALL be raised for the missing fields.

#### Scenario: New fields present but null

- **Given** an `about.json` where any of the five new fields is set to `null`
- **When** a generator inspects that field
- **Then** the system SHALL treat the `null` value as "not set" and SHALL fall
  back to the pre-existing behavior for that field.

### Requirement: Non-breaking schema validation

The `schemas/about.schema.json` JSON Schema SHALL define the five new fields as
optional properties with correct types: `githubReadmeSummary`, `linkedinHeadline`,
and `cvHeadline` as `string`; `portfolioHighlights` as an `array` of `string`;
and `whatIBuildVariants` as an `object`. The schema MUST NOT add any of these
fields to its `required` array (which remains `["username", "tagline",
"description"]`) and MUST keep `additionalProperties: true` so pre-existing data
validates unchanged.

#### Scenario: Legacy data validates unchanged

- **Given** an `about.json` produced before this change (without the new fields)
- **When** it is validated against `schemas/about.schema.json`
- **Then** validation SHALL pass without errors.

#### Scenario: Correctly typed new fields validate

- **Given** an `about.json` containing the new fields with their defined types
  (strings for the three headline fields, an array of strings for
  `portfolioHighlights`, an object for `whatIBuildVariants`)
- **When** it is validated against the schema
- **Then** validation SHALL pass.

#### Scenario: Wrong field type fails validation

- **Given** an `about.json` where a new field has an incorrect type (e.g.
  `portfolioHighlights` set to a string instead of an array)
- **When** it is validated against the schema
- **Then** validation SHALL fail for that field.

### Requirement: GitHub README generator uses githubReadmeSummary when present

`generators/generate_github_readme.py` SHALL check `about.get('githubReadmeSummary')`
in its `render_about` function. When the value is present and non-null, the
generator MUST render the profile display text as
`**{username}** — {githubReadmeSummary}`. When the value is absent or null, the
generator MUST fall back to the current behavior using
`about.get('headline', about.get('tagline', ''))`.

#### Scenario: Summary present

- **Given** `about.githubReadmeSummary` is a non-empty string
- **When** `render_about` runs
- **Then** the output SHALL display the username followed by the
  `githubReadmeSummary` value.

#### Scenario: Summary absent falls back to headline/tagline

- **Given** `about.githubReadmeSummary` is absent or null
- **When** `render_about` runs
- **Then** the output SHALL use `headline`, or `tagline` if `headline` is absent,
  exactly as before this change.

### Requirement: LinkedIn generator uses linkedinHeadline with 220-char handling

`generators/generate_linkedin.py` SHALL check `about.get('linkedinHeadline')` in
its `main` function. When present and non-null, the generator MUST use the value
for the LinkedIn headline; LinkedIn headlines are limited to 220 characters, so
the generator MUST NOT emit a headline longer than 220 characters (truncating or
warning when the provided value exceeds the limit). When absent or null, the
generator MUST fall back to the existing truncation behavior applied to
`about.get('headline', about.get('tagline', ''))`.

#### Scenario: LinkedIn headline present and within limit

- **Given** `about.linkedinHeadline` is a non-null string of 220 characters or
  fewer
- **When** the LinkedIn copy is generated
- **Then** the output headline SHALL be the `linkedinHeadline` value used
  directly.

#### Scenario: LinkedIn headline present but exceeds 220 characters

- **Given** `about.linkedinHeadline` is a non-null string longer than 220
  characters
- **When** the LinkedIn copy is generated
- **Then** the emitted headline SHALL NOT exceed 220 characters (the generator
  truncates or warns).

#### Scenario: LinkedIn headline absent falls back to truncation

- **Given** `about.linkedinHeadline` is absent or null
- **When** the LinkedIn copy is generated
- **Then** the generator SHALL apply the existing truncation logic to
  `headline` (or `tagline`) as before this change.

### Requirement: CV generator uses cvHeadline in the design section when present

`generators/generate_cv.py` SHALL check `about.get('cvHeadline')` in its `main`
function. When present and non-null, the generator MUST use the value as the
headline in the RenderCV `design:` section
(`headline: {escape_yaml_string(cvHeadline)}`). When absent or null, the
generator MUST fall back to the current behavior using
`about.get('headline', about.get('tagline', ''))`.

#### Scenario: CV headline present

- **Given** `about.cvHeadline` is a non-null string
- **When** the CV is generated
- **Then** the `design:` section headline SHALL be the `cvHeadline` value,
  YAML-escaped.

#### Scenario: CV headline absent falls back

- **Given** `about.cvHeadline` is absent or null
- **When** the CV is generated
- **Then** the `design:` headline SHALL use `headline`, or `tagline` if
  `headline` is absent, exactly as before this change.

### Requirement: portfolioHighlights must reference valid project names

When `about.portfolioHighlights` is present, every entry SHALL be the `name` of
an existing project in `data/projects.json`, and the list SHOULD contain at most
6 project names. The system SHOULD detect entries that do not match any project
name and warn on the mismatch rather than silently featuring a non-existent
project.

#### Scenario: All highlights reference existing projects

- **Given** `about.portfolioHighlights` contains names that all match a `name`
  in `projects.json`
- **When** highlights are resolved to project entries
- **Then** each highlight SHALL map to exactly one existing project.

#### Scenario: A highlight references a non-existent project

- **Given** `about.portfolioHighlights` contains a name with no matching project
  in `projects.json`
- **When** highlights are validated
- **Then** the system SHALL report a warning identifying the unmatched name.

#### Scenario: portfolioHighlights absent shows all projects

- **Given** `about.portfolioHighlights` is absent or null
- **When** the portfolio consumes the data
- **Then** the portfolio SHALL fall back to showing all projects from
  `projects.json`.
