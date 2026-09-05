# Portfolio Generation Specification

## Purpose

Defines the contract for `generators/generate_portfolio.py`, which produces `output/portfolio.md` by selecting projects from `data/projects.json` using the `portfolioHighlights` selector defined in `data/about.json`.

## Requirements

### Requirement: Portfolio generator produces output/portfolio.md

`generators/generate_portfolio.py` SHALL read `data/projects.json` and `data/about.json`, apply the `portfolioHighlights` selector, and write the result to `output/portfolio.md`. The generator MUST NOT write to any path outside `output/`.

#### Scenario: Generator runs and writes correct path

- GIVEN `data/projects.json` and `data/about.json` are valid
- WHEN `generate_portfolio.py` is executed
- THEN `output/portfolio.md` SHALL be created or overwritten
- AND no file SHALL be written to the repository root

### Requirement: portfolioHighlights selector filters projects

When `about.portfolioHighlights` is a non-null, non-empty array, `output/portfolio.md` MUST include only the projects whose `name` matches an entry in the array, preserving the order defined in `portfolioHighlights`. Projects not named in the array MUST NOT appear in the output.

#### Scenario: Filtered portfolio with matching highlights

- GIVEN `about.portfolioHighlights` is `["Project A", "Project C"]`
- AND `data/projects.json` contains projects named "Project A", "Project B", and "Project C"
- WHEN `generate_portfolio.py` runs
- THEN `output/portfolio.md` SHALL contain "Project A" and "Project C" in that order
- AND "Project B" SHALL NOT appear in the output

#### Scenario: Highlight order preserved

- GIVEN `about.portfolioHighlights` is `["Project C", "Project A"]`
- AND both projects exist in `data/projects.json`
- WHEN `generate_portfolio.py` runs
- THEN "Project C" SHALL appear before "Project A" in `output/portfolio.md`

### Requirement: Null or absent portfolioHighlights shows all projects

When `about.portfolioHighlights` is `null` or absent, `output/portfolio.md` MUST include all projects from `data/projects.json` in their source-file order.

#### Scenario: portfolioHighlights null — all projects shown

- GIVEN `about.portfolioHighlights` is `null`
- WHEN `generate_portfolio.py` runs
- THEN `output/portfolio.md` SHALL contain every project from `data/projects.json`

#### Scenario: portfolioHighlights absent — all projects shown

- GIVEN `about.json` does not declare the `portfolioHighlights` field
- WHEN `generate_portfolio.py` runs
- THEN `output/portfolio.md` SHALL contain every project from `data/projects.json`

### Requirement: Unmatched highlight name emits a warning

When an entry in `portfolioHighlights` does not match any `name` in `data/projects.json`, the generator MUST emit a warning identifying the unmatched name. The unmatched entry MUST be silently skipped — the remaining matched projects SHALL still be rendered. The generator MUST NOT raise an unhandled exception for an unmatched name.

#### Scenario: One highlight name not found in projects

- GIVEN `about.portfolioHighlights` contains `"NonExistentProject"` alongside valid names
- WHEN `generate_portfolio.py` runs
- THEN a warning SHALL be emitted identifying `"NonExistentProject"` as unmatched
- AND valid matched projects SHALL still appear in `output/portfolio.md`
- AND the generator SHALL exit successfully (zero exit code / no exception)

#### Scenario: All highlights unmatched

- GIVEN `about.portfolioHighlights` contains only names that do not match any project
- WHEN `generate_portfolio.py` runs
- THEN a warning SHALL be emitted for each unmatched name
- AND `output/portfolio.md` SHALL be written (possibly empty or with a fallback heading)

### Requirement: Portfolio project entry content

Each project entry in `output/portfolio.md` MUST include at minimum: the project `name`, `description`, and `tech` list. If a `url` field is non-empty, it MUST be rendered as a link. `highlights` entries, when present, MUST be rendered as a list under the project entry.

#### Scenario: Full project entry rendered

- GIVEN a project with `name`, `description`, `tech`, a non-empty `url`, and `highlights`
- WHEN `generate_portfolio.py` renders the project
- THEN the output SHALL include the name, description, tech list, a hyperlink to the url, and each highlight as a list item

#### Scenario: Project with empty url rendered without link

- GIVEN a project where `url` is an empty string
- WHEN `generate_portfolio.py` renders the project
- THEN no broken or empty link SHALL appear in the output for that project

### Requirement: Portfolio render functions are pure and testable

The portfolio generator MUST expose at least two pure functions: one that computes the filtered project list (`compute_portfolio_projects`) and one that renders the markdown content (`render_portfolio`). These functions MUST accept plain dict/list arguments and return strings or lists without performing any file I/O.

#### Scenario: compute_portfolio_projects with highlights

- GIVEN a list of project dicts and a list of highlight names
- WHEN `compute_portfolio_projects(projects, highlights)` is called
- THEN it SHALL return only the projects whose `name` is in `highlights`, in highlight order

#### Scenario: render_portfolio returns a non-empty string

- GIVEN a valid `about` dict and a non-empty list of project dicts
- WHEN `render_portfolio(about, projects)` is called
- THEN it SHALL return a non-empty markdown string without writing any file
