# Component Registry Specification

## Purpose

Defines a single, plugin-based discovery mechanism for both generators and
publishers, replacing the two independently maintained lists that have
already diverged (`cli.py`'s `GENERATORS` omits `generate_portfolio_data`
while `generate_all.py` includes it).

## Requirements

### Requirement: One registry for generators and publishers

The system MUST expose exactly one discovery mechanism (e.g. Python entry
points) that both `profile generate` / `profile generate all` and any
standalone pipeline entry point consult. No second, independently
maintained list of components MUST exist.

#### Scenario: Single source enumerates all components

- GIVEN generators and publishers registered via entry points
- WHEN the registry is queried for the full component list
- THEN both `profile generate all` and any direct pipeline invocation SHALL
  enumerate the identical set

#### Scenario: Divergence bug is structurally impossible

- GIVEN `portfolio_data` is registered as a publisher entry point
- WHEN `profile generate all` runs
- THEN it SHALL execute the same registered set an equivalent pipeline
  invocation would run
- AND no code path SHALL maintain a second, separately edited list of
  components

### Requirement: Adding a component requires no core edits

Registering a new generator or publisher MUST require only an entry-point
declaration (e.g. in `pyproject.toml`), not an edit to a hardcoded dict
inside `cli.py` or `generate_all.py`.

#### Scenario: New generator registered via entry point

- GIVEN a new generator is declared as an entry point and no other file is
  modified
- WHEN the registry is queried
- THEN the new generator SHALL appear in the enumerated component list

### Requirement: Registry distinguishes generators from publishers

Each registered component MUST declare its kind (`generator` or
`publisher`). `profile generate` MUST only invoke `generator`-kind
components; `profile publish` MUST only invoke `publisher`-kind components.

#### Scenario: generate does not invoke publishers

- GIVEN `portfolio_data` is registered as a `publisher`-kind component
- WHEN `profile generate all` runs
- THEN it SHALL NOT invoke `portfolio_data`
- AND `profile publish all` SHALL invoke it

#### Scenario: Unknown kind is rejected

- GIVEN an entry point declares a kind other than `generator` or `publisher`
- WHEN the registry loads
- THEN it SHALL reject the entry point with a descriptive error rather than
  silently invoking it from either command
