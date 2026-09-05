# Proposal: Unified Generator CLI

## Intent

Generator invocation is scattered and unmemorable. Today you must know the exact
module paths (`python -m generators.generate_all`, `python -m generators.validate`,
and four individual `generate_*` modules), and the output-freshness check lives
only in CI as an inline `git diff` step — there is no local equivalent. This
change adds a single, discoverable entry point (`profile`) that wraps the
existing generator `main()` functions behind clear subcommands, without
duplicating any generation logic.

## Scope

### In Scope
- **`generators/cli.py`**: an `argparse`-based CLI exposing `generate`,
  `validate`, `check`, and `list` subcommands.
- **`generate [target]`**: run one generator or all of them (default `all`),
  preserving the current `generate_all` ordering.
- **`validate`**: delegate to `generators.validate.main()`, propagating its exit code.
- **`check`**: local CI-parity gate — validate, then regenerate all output and
  fail if committed `output/` drifts (`git diff --exit-code -- output/`).
- **`list`**: enumerate available generation targets.
- **Console entry point**: `[project.scripts] profile = "generators.cli:main"`
  so `profile ...` works after `pip install -e .`, plus `python -m generators.cli`.
- **CI integration**: the `validate.yml` workflow drives data validation and the
  output-freshness regeneration through the CLI (`python -m generators.cli`)
  instead of calling the individual modules directly, so CI exercises the same
  entry point users run locally.

### Out of Scope
- **`--data-dir` / `--output-dir` overrides** — explicit non-goal for this
  change. Generators keep their hardcoded module-level paths; adding path
  injection is a separate, additive future change.
- Rewriting or refactoring generator logic.
- Deploy automation (README push to `JohnyYen/JohnyYen` stays manual).
- Watch mode, TUI, or a task runner (Makefile).

## Capabilities

### New Capabilities
- `generator-cli`: unified command-line interface over the existing generators.

### Modified Capabilities
- `generator-tooling`: CI drives data validation and output-freshness
  regeneration through the generator CLI. Existing `python -m
  generators.generate_all`, `python -m generators.validate`, and individual
  `generate_*` invocations remain unchanged (backward compatible).

## Approach

`cli.py` is a thin orchestration layer. It imports the four generator modules
plus `validate` and maps subcommands to their `main()` callables via a
module-level `GENERATORS` registry (insertion-ordered to match `generate_all`).
`check` reuses the proven CI pattern: run validate, regenerate, then shell out to
`git diff --exit-code -- output/`. Only the Python stdlib (`argparse`,
`subprocess`) is used — the single-runtime-dependency discipline (`jsonschema`)
is preserved. The console script requires including the `generators` package in
the setuptools build (`packages = ["generators"]`), the one packaging touch.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `generators/cli.py` | New | argparse CLI wrapping existing `main()`s |
| `pyproject.toml` | Modified | `[project.scripts]` + `[tool.setuptools] packages` |
| `tests/test_cli.py` | New | subcommand dispatch + exit-code tests (side-effect free) |
| `README.md` | Modified | document `profile` / `python -m generators.cli` usage |
| `.github/workflows/validate.yml` | Modified | validate + freshness steps run via the CLI |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Console entry point breaks the "not a distributable package" stance | Low | Include only `generators`; `python -m generators.cli` works without install |
| CLI duplicates generator logic and drifts | Low | Wrap `main()`s directly; zero re-implementation |
| `check` tests touch git/filesystem | Med | Tests monkeypatch the registry + git-diff helper; no real IO |
| Scope creep into path overrides | Med | Explicit non-goal; enforced in spec |

## Rollback Plan

Revert the change commit(s). `cli.py`, the `[project.scripts]` entry, and the
`packages` key are purely additive — removing them restores the prior state with
no effect on data, generators, or the existing `python -m` invocations.

## Dependencies

- None new. Uses stdlib `argparse` and `subprocess`.

## Success Criteria

- [ ] `python -m generators.cli generate` regenerates all outputs, exits zero.
- [ ] `profile generate cv` runs only the CV generator after `pip install -e .`.
- [ ] `profile validate` mirrors `python -m generators.validate` exit codes.
- [ ] `profile check` fails on stale `output/` or invalid data, passes when fresh.
- [ ] `profile list` prints the available targets.
- [ ] Existing `python -m generators.generate_all` and individual invocations still work.
- [ ] No new runtime dependency; full pytest suite passes.
