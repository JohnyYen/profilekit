# GitHub README Generation Specification

## Purpose

Defines the contract for `generators/generate_github_readme.py`: the centered HTML structure it MUST emit, the icon-row rendering rules, the bundled asset reference, and the output-path guard.

## Requirements

### Requirement: Centered HTML document structure

The system MUST emit `output/github-readme.md` as a centered HTML document with the following top-level sections, in order:

1. `<h1 align="center">` greeting derived from `about.json`
2. `<h2 align="center">` professional headline
3. An About block containing a local pixel-mario image and prose summary
4. A "What I focus on" bullet list
5. Per-category technology icon rows
6. Text Experience section
7. Text "Currently learning" section
8. A closing invite/quote

The generator MUST NOT write to the repository root `README.md`.

#### Scenario: Full document rendered

- GIVEN `data/about.json`, `data/skills.json`, and `data/experience.json` are populated
- WHEN `generate_github_readme.py` runs
- THEN `output/github-readme.md` SHALL contain an `<h1 align="center">` element, an `<h2 align="center">` element, and all eight structural sections
- AND the file written SHALL be `output/github-readme.md` — root `README.md` SHALL remain unmodified

#### Scenario: Root README regression guard

- GIVEN root `README.md` exists with maintainer content
- WHEN `generate_github_readme.py` runs
- THEN `README.md` in the repository root SHALL NOT be created, overwritten, or truncated

### Requirement: Bundled pixel-mario asset reference

The generator MUST reference the pixel-mario gif via a stable in-repo relative path (`assets/pixel-mario.gif`). The generator MUST NOT hardcode an external raw URL for this asset. The `assets/` directory and `pixel-mario.gif` MUST be committed to the repository.

#### Scenario: Asset referenced by relative path

- GIVEN `assets/pixel-mario.gif` exists in the repository
- WHEN the About block is rendered
- THEN the emitted HTML SHALL include an `<img>` tag whose `src` is a relative path pointing to `assets/pixel-mario.gif`
- AND no external URL for the Mario gif SHALL appear in the output

#### Scenario: Asset file absent raises a clear error

- GIVEN `assets/pixel-mario.gif` does not exist
- WHEN the generator runs
- THEN it SHALL raise an error or warning identifying the missing asset
- AND it SHALL NOT silently emit a broken `<img>` tag pointing to a missing path

### Requirement: Per-category icon rows

For each skill category that has at least one icon-bearing entry, the generator MUST emit a `<div align="center">` containing one `<img>` per icon-bearing skill. Categories where no entry carries an `icon` or `iconUrl` field MUST NOT produce an icon `<div>`.

#### Scenario: Category with icon-bearing skills renders icon row

- GIVEN a skill category contains entries with `icon` or `iconUrl` fields
- WHEN the README is generated
- THEN a `<div align="center">` SHALL appear for that category containing one `<img>` per icon-bearing entry

#### Scenario: Conceptual category produces no icon block

- GIVEN a skill category (e.g. "Software Design", "AI-Driven Development") has no entries with `icon` or `iconUrl`
- WHEN the README is generated
- THEN no `<div align="center">` icon block SHALL be emitted for that category
- AND the category MAY be rendered as plain text or omitted entirely from the icon section

#### Scenario: Mixed category — only icon-bearing skills appear in the icon row

- GIVEN a category contains a mix of icon-bearing and plain-string entries
- WHEN the icon row for that category is rendered
- THEN only entries with `icon` or `iconUrl` SHALL appear as `<img>` elements
- AND string-only entries SHALL NOT emit a broken or empty `<img>` tag

### Requirement: Icon URL source rules

For each icon-bearing skill entry the generator MUST apply the following rules in priority order:

1. If `iconUrl` is present, use it verbatim as the `src`.
2. Else if `icon` is present, compose `https://skillicons.dev/icons?i=<icon>` as the `src`.
3. Otherwise (bare string or no icon field) the skill MUST be omitted from icon rows; no `<img>` is emitted.

The generator MUST NOT emit a broken or empty `<img>` for a skill with neither `icon` nor `iconUrl`.

#### Scenario: icon field renders skillicons URL

- GIVEN a skill entry `{"name": "NestJS", "icon": "nestjs"}`
- WHEN the icon row is rendered
- THEN the emitted `<img src>` SHALL be `https://skillicons.dev/icons?i=nestjs`

#### Scenario: iconUrl field renders verbatim URL

- GIVEN a skill entry `{"name": "Strapi", "iconUrl": "https://devicons.railway.com/i/strapi.svg"}`
- WHEN the icon row is rendered
- THEN the emitted `<img src>` SHALL be `https://devicons.railway.com/i/strapi.svg` exactly

#### Scenario: iconUrl takes priority over icon

- GIVEN a skill entry with both `icon` and `iconUrl` set
- WHEN the icon row is rendered
- THEN the emitted `<img src>` SHALL use `iconUrl` verbatim, not the skillicons URL

#### Scenario: Plain string entry emits no img

- GIVEN a skill entry is a bare string (e.g. `"Clean Architecture"`)
- WHEN icon rows are rendered
- THEN no `<img>` element SHALL be emitted for that entry

### Requirement: Icon img height

Every `<img>` emitted in an icon row MUST carry `height="60"` to match the target profile style. Width MUST NOT be explicitly set (let the browser scale proportionally).

#### Scenario: Icon img has correct height attribute

- GIVEN an icon-bearing skill entry
- WHEN the icon row HTML is rendered
- THEN every `<img>` in that row SHALL include `height="60"` and SHALL NOT include an explicit `width` attribute
