# Skills Data Model Specification

## Purpose

Defines the contract for skill entries in `data/skills.json`, the schema in `schemas/skills.schema.json`, and the normalization behavior all consumers MUST implement. Entries may be plain strings (no icon) or structured objects; all consumers MUST handle both shapes without breaking.

## Requirements

### Requirement: Dual-shape skill entry

`data/skills.json` entries under `details` MUST be valid as either a plain string OR a structured object `{name, icon?, iconUrl?}`. A plain string represents a skill with no icon. An object carries the skill name plus optional icon metadata. Both shapes MUST coexist within the same category.

#### Scenario: Object entry is valid

- GIVEN a `details` entry `{"name": "NestJS", "icon": "nestjs"}`
- WHEN `data/skills.json` is validated against `schemas/skills.schema.json`
- THEN validation SHALL pass

#### Scenario: String entry is valid

- GIVEN a `details` entry `"Clean Architecture"`
- WHEN `data/skills.json` is validated against `schemas/skills.schema.json`
- THEN validation SHALL pass

#### Scenario: Mixed entries in same category are valid

- GIVEN a category whose `details` array contains both string and object entries
- WHEN the file is validated
- THEN validation SHALL pass for the entire array

#### Scenario: Object entry without icon or iconUrl is valid

- GIVEN a `details` entry `{"name": "Docker"}` (no `icon`, no `iconUrl`)
- WHEN the file is validated
- THEN validation SHALL pass — icon fields are optional

### Requirement: Widened schema accepts oneOf per entry

`schemas/skills.schema.json` MUST widen the `details.items` definition to `oneOf[string, object]`. The object branch MUST require `name` (string) and declare `icon` (string, optional) and `iconUrl` (string, optional) as additional properties. No existing required fields on the schema MUST be altered. Existing `skills.json` files that use only plain strings MUST continue to validate without change.

#### Scenario: Schema rejects invalid entry type

- GIVEN a `details` entry is a number (e.g. `42`)
- WHEN the file is validated
- THEN validation SHALL fail for that entry

#### Scenario: Object entry missing name fails validation

- GIVEN a `details` entry `{"icon": "nestjs"}` (no `name`)
- WHEN the file is validated
- THEN validation SHALL fail — `name` is required on the object branch

#### Scenario: Legacy all-string file validates unchanged

- GIVEN a `skills.json` whose every `details` entry is a plain string
- WHEN validated against the updated schema
- THEN validation SHALL pass without errors

### Requirement: Consumer skill-name normalization

Every consumer of `data/skills.json` (`generate_github_readme.py`, `generate_linkedin.py`, `generate_cv.py`) MUST resolve the display name of each entry using the following rule: if the entry is a string, use it directly; if the entry is an object, use `entry["name"]`. No consumer SHALL assume entries are always strings. No consumer SHALL raise an unhandled exception when encountering either shape.

#### Scenario: LinkedIn generator handles object entries

- GIVEN `skills.json` contains object entries in one or more categories
- WHEN `generate_linkedin.py` runs
- THEN `output/linkedin.md` SHALL list the skill display names identically to when the entries were plain strings
- AND no exception SHALL be raised

#### Scenario: CV generator handles object entries

- GIVEN `skills.json` contains object entries
- WHEN `generate_cv.py` runs
- THEN `output/cv.md` and `output/cv.yml` SHALL contain the same skill text as when entries were plain strings
- AND no exception SHALL be raised

#### Scenario: GitHub README generator handles string entries

- GIVEN `skills.json` contains plain-string entries in a category
- WHEN `generate_github_readme.py` renders that category
- THEN string entries SHALL be resolved to their text value
- AND no `<img>` SHALL be emitted for them (they carry no icon)

### Requirement: Consumer output regression stability

Replacing plain-string entries with equivalent `{name, icon?}` objects in `data/skills.json` MUST NOT change the skill-name text output of `generate_linkedin.py` or `generate_cv.py`. Both generators MUST produce byte-equivalent skill sections before and after the data migration, given the same `name` value.

#### Scenario: LinkedIn skill text unchanged after data migration

- GIVEN a category whose entries have been converted from strings to `{name, icon}` objects with identical `name` values
- WHEN `generate_linkedin.py` runs
- THEN the skills section in `output/linkedin.md` SHALL be byte-equivalent to the pre-migration output

#### Scenario: CV skill text unchanged after data migration

- GIVEN the same migration scenario as above applied to `generate_cv.py`
- WHEN `generate_cv.py` runs
- THEN the skills section in `output/cv.md` SHALL be byte-equivalent to the pre-migration output
