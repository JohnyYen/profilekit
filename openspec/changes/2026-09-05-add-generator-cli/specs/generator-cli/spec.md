# Delta for Generator CLI

## ADDED Requirements

### Requirement: Unified CLI Entry Point

The project MUST provide a single command-line entry point implemented in
`generators/cli.py` that dispatches to subcommands. It MUST be invocable both as
a module (`python -m generators.cli`) and, after `pip install -e .`, as a
console script named `profile`. The entry point MUST expose a `main(argv=None)`
function that returns an integer exit code and that `sys.exit`s with that code
when run as a script. Invoking the CLI with no subcommand MUST print usage help
and exit non-zero. The CLI MUST use only the Python standard library (no new
runtime dependency).

#### Scenario: Module invocation runs the CLI

- GIVEN a valid repository checkout
- WHEN `python -m generators.cli list` is executed from the repository root
- THEN the CLI SHALL run and exit zero

#### Scenario: Console script is exposed

- GIVEN the project has been installed with `pip install -e .`
- WHEN `profile list` is executed
- THEN the `profile` command SHALL resolve to `generators.cli:main` and exit zero

#### Scenario: No subcommand prints help

- GIVEN the CLI is invoked
- WHEN no subcommand is provided
- THEN usage help SHALL be printed
- AND the process SHALL exit non-zero

### Requirement: Generate Subcommand

The CLI MUST provide a `generate` subcommand accepting an optional positional
`target`. Valid targets are `all` (default), `github-readme`, `linkedin`,
`portfolio`, and `cv`. When `target` is `all`, every generator MUST run in the
same order as `generators.generate_all` (`github-readme`, `linkedin`,
`portfolio`, `cv`). When `target` names a single generator, only that generator
MUST run. An unknown target MUST cause a non-zero exit with an error message. If
any invoked generator raises, the command MUST exit non-zero and MUST identify
the failing target.

#### Scenario: Generate all targets

- GIVEN valid data files
- WHEN `generate` (or `generate all`) runs
- THEN each generator's `main()` SHALL be invoked once in `generate_all` order
- AND the command SHALL exit zero

#### Scenario: Generate a single target

- GIVEN valid data files
- WHEN `generate cv` runs
- THEN only the CV generator SHALL be invoked
- AND the command SHALL exit zero

#### Scenario: Unknown target rejected

- GIVEN the CLI is invoked
- WHEN `generate bogus` runs
- THEN the command SHALL exit non-zero
- AND an error message SHALL name the invalid target

#### Scenario: Generator failure propagates

- GIVEN a generator raises during execution
- WHEN `generate` runs
- THEN the command SHALL exit non-zero
- AND the error output SHALL identify which target failed

### Requirement: Validate Subcommand

The CLI MUST provide a `validate` subcommand that invokes
`generators.validate.main()` and exits with its return code (0 on success, 1 on
any schema failure). Behavior and output MUST match direct invocation of
`python -m generators.validate`.

#### Scenario: Validation passes

- GIVEN all data files satisfy their schemas
- WHEN `validate` runs
- THEN the command SHALL exit zero

#### Scenario: Validation fails

- GIVEN at least one data file violates its schema
- WHEN `validate` runs
- THEN the command SHALL exit non-zero with the same code as `generators.validate.main()`

### Requirement: Check Subcommand

The CLI MUST provide a `check` subcommand that runs local CI-parity
verification: first schema validation, then regeneration of all outputs, then a
freshness comparison of the committed `output/` tree against freshly generated
content via `git diff --exit-code -- output/`. The command MUST exit non-zero if
validation fails OR if the output tree has drifted, and exit zero only when both
pass.

#### Scenario: Clean repository passes check

- GIVEN valid data and a committed `output/` matching fresh generation
- WHEN `check` runs
- THEN validation SHALL pass, regeneration SHALL run, `git diff` SHALL exit zero
- AND the command SHALL exit zero

#### Scenario: Stale output fails check

- GIVEN `output/` differs from what the generators would produce
- WHEN `check` runs
- THEN the command SHALL exit non-zero
- AND the failure SHALL indicate output drift

#### Scenario: Invalid data fails check before drift

- GIVEN a data file violates its schema
- WHEN `check` runs
- THEN validation SHALL fail and the command SHALL exit non-zero

### Requirement: List Subcommand

The CLI MUST provide a `list` subcommand that prints the available generation
targets (the single-generator target names) to standard output and exits zero.

#### Scenario: List targets

- GIVEN the CLI is invoked
- WHEN `list` runs
- THEN each generation target name SHALL be printed
- AND the command SHALL exit zero

### Requirement: Backward-Compatible Invocation

Adding the CLI MUST NOT change existing invocation paths. `python -m
generators.generate_all`, `python generators/generate_all.py`, `python -m
generators.validate`, and each individual `python -m generators.generate_*`
module MUST continue to work and produce identical artifacts. The CLI MUST NOT
introduce `--data-dir` or `--output-dir` options in this change.

#### Scenario: Legacy generate_all still works

- GIVEN the CLI has been added
- WHEN `python -m generators.generate_all` is executed
- THEN all outputs SHALL be produced exactly as before the change

#### Scenario: No path override flags

- GIVEN the CLI is invoked with `--help` on any subcommand
- WHEN the help is displayed
- THEN no `--data-dir` or `--output-dir` option SHALL be present
