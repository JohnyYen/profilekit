# Design: Unified Generator CLI

## Architecture Decision: Thin Orchestration Layer

`cli.py` adds **no** generation logic. It imports the existing generator modules
and maps subcommands to their `main()` callables. This keeps a single source of
truth (the generators) and guarantees the CLI can never drift from direct
module invocation.

```
profile <subcommand> ─► generators/cli.py:main(argv)
                          ├─ generate [target] ─► GENERATORS[target]()  (or all, in order)
                          ├─ validate           ─► generators.validate.main()
                          ├─ check              ─► validate → generate all → git diff
                          └─ list               ─► print(GENERATORS.keys())
```

### Target registry

A module-level insertion-ordered dict is the single source for target names and
ordering, matching `generate_all`:

```python
GENERATORS = {
    "github-readme": github_readme.main,
    "linkedin":      linkedin.main,
    "portfolio":     portfolio.main,
    "cv":            cv.main,
}
```

`generate all` iterates `GENERATORS.values()` in order; `generate <target>`
looks up one entry. `list` prints `GENERATORS.keys()`. Adding a future generator
is a one-line registry edit.

## Decision: argparse, no new dependency

Four subcommands do not justify `click`/`typer`. `argparse` subparsers cover
positional `target`, `--help`, and exit-code semantics. The project keeps its
single runtime dependency (`jsonschema`). Rejected: `typer` (adds `click` +
`typing-extensions` transitive deps for marginal ergonomics).

## Decision: dispatch via testable helpers

Each subcommand is a standalone function returning `int`:
`cmd_generate(target) -> int`, `cmd_validate() -> int`, `cmd_check() -> int`,
`cmd_list() -> int`. `main(argv=None)` builds the parser, dispatches, returns the
code. The `__main__` guard does `sys.exit(main())`. This mirrors the existing
`validate.main() -> int` contract and lets tests call functions directly and
assert return codes without spawning subprocesses.

## Decision: `check` shells out to git for freshness

`check` reproduces the CI freshness gate locally: `cmd_validate()`, then run all
generators, then `subprocess.run(["git", "diff", "--exit-code", "--", "output/"])`.
The git call is isolated in a `_git_output_is_clean() -> bool` helper so tests
monkeypatch it (no real git/filesystem dependency). Validation short-circuits:
if `cmd_validate()` is non-zero, `check` returns immediately without regenerating.

## Decision: console script + module invocation

`[project.scripts] profile = "generators.cli:main"` gives the ergonomic `profile`
command after `pip install -e .`. Because the repo historically declared
`py-modules = []` ("not a distributable package"), the entry point needs the
package included: `[tool.setuptools] packages = ["generators"]`. `python -m
generators.cli` remains the install-free path (what CI and tests use), so the
console script is a convenience, not a hard requirement.

## Testing Strategy (Strict TDD)

Tests are side-effect free — they monkeypatch `cli.GENERATORS` with spy
callables and monkeypatch `cli.validate.main` and `cli._git_output_is_clean`, so
no real files are written and git is never invoked.

| Test | Asserts |
|------|---------|
| `build_parser` / no-subcommand | parser exists; empty argv → non-zero + help |
| generate all order | spies called once each, in `generate_all` order |
| generate single | only the named spy called |
| generate unknown target | non-zero, message names target |
| generator raises | non-zero, message names failing target |
| validate delegation | returns patched `validate.main` code (0 and 1) |
| check clean | validate ok + git clean → 0 |
| check drift | validate ok + git dirty → non-zero |
| check invalid data | validate non-zero → returns early non-zero, generators not run |
| list | prints all target names, exit 0 |
| no path-override flags | `--help` text has no `--data-dir`/`--output-dir` |

Coverage threshold (80%) must hold; `cli.py` is small and fully exercised.

## Non-Goals (enforced)

- No `--data-dir` / `--output-dir` — generators keep module-level paths.
- No refactor of generator internals.
- No deploy automation, watch mode, or Makefile.
