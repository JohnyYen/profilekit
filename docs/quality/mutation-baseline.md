# Mutation testing baseline

Line and branch coverage say which code the tests *ran*. Mutation testing says
which code the tests *check*: [mutmut](https://github.com/boxed/mutmut) makes
small changes to the source (flip a condition, drop an argument, replace a
string) and re-runs the tests that exercise it. A mutant the tests do not notice
"survives", and each survivor is a behavior nothing asserts.

## How to run it

```bash
uv sync --extra dev
uv run mutmut run            # full run, about 4 minutes on 12 cores
uv run mutmut results        # list survivors
uv run mutmut show <name>    # the diff of one mutant
```

Configuration lives in `[tool.mutmut]` in `pyproject.toml`:

- Only `src/profilekit/` is mutated.
- The unit suite runs; `tests/e2e` is excluded, because it builds and installs
  the distribution, which is far too slow to repeat for every mutant.
- `--no-cov` drops the coverage gate, which a partial test selection would fail.
- `tests/test_generator_output_boundary.py::test_every_generator_accepts_an_explicit_output_dir`
  is deselected: it inspects generator signatures, which mutmut replaces with
  its own trampolines, so it fails on the mutated copy before any mutant runs.
- Repository files that unit tests read (`data/`, `docs/`, `apps/`, CI
  workflows, top-level docs) are copied into mutmut's working copy, `mutants/`.

`mutants/` is gitignored and regenerated on every run.

Score is `(killed + timeout) / total`, the same formula mutmut uses. "No tests"
mutants sit in code no selected test calls and count as not killed.

## Baseline

- Date: 2026-10-23
- Base commit: `054bb9e`
- mutmut 3.8.0, Python 3.14, full run over every module (3 min 38 s)

| Module | Mutants | Killed | Survived | Timeout | No tests | Other | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cli.py` | 664 | 429 | 235 | 0 | 0 | 0 | 64.6% |
| `config.py` | 51 | 39 | 12 | 0 | 0 | 0 | 76.5% |
| `context.py` | 137 | 130 | 7 | 0 | 0 | 0 | 94.9% |
| `generate_cv.py` | 504 | 407 | 93 | 0 | 4 | 0 | 80.8% |
| `generate_github_readme.py` | 320 | 267 | 53 | 0 | 0 | 0 | 83.4% |
| `generate_linkedin.py` | 285 | 242 | 43 | 0 | 0 | 0 | 84.9% |
| `generate_portfolio.py` | 137 | 109 | 28 | 0 | 0 | 0 | 79.6% |
| `icons.py` | 78 | 34 | 44 | 0 | 0 | 0 | 43.6% |
| `links.py` | 79 | 40 | 39 | 0 | 0 | 0 | 50.6% |
| `manifest.py` | 148 | 131 | 17 | 0 | 0 | 0 | 88.5% |
| `publish.py` | 274 | 167 | 107 | 0 | 0 | 0 | 60.9% |
| `publishers/filesystem.py` | 231 | 187 | 34 | 0 | 10 | 0 | 81.0% |
| `publishers/manual.py` | 69 | 35 | 24 | 0 | 10 | 0 | 50.7% |
| `registry.py` | 75 | 61 | 14 | 0 | 0 | 0 | 81.3% |
| `render.py` | 217 | 125 | 92 | 0 | 0 | 0 | 57.6% |
| `scaffold.py` | 52 | 31 | 21 | 0 | 0 | 0 | 59.6% |
| `secrets.py` | 51 | 32 | 17 | 0 | 2 | 0 | 62.7% |
| `utils.py` | 115 | 81 | 34 | 0 | 0 | 0 | 70.4% |
| `validate.py` | 204 | 102 | 102 | 0 | 0 | 0 | 50.0% |
| **Total** | 3691 | 2649 | 1016 | 0 | 26 | 0 | **71.8%** |

Most survivors are mutated error and status messages: the suite asserted that
an error was raised or a command failed, not what it told the operator.

## After the mutant-killing tests

- Date: 2026-10-23
- Commit: `b04822a` (the `tests/test_mutation_*.py` files)
- Same configuration, full run over every module (3 min 51 s)

| Module | Mutants | Killed | Survived | Timeout | No tests | Other | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cli.py` | 664 | 633 | 31 | 0 | 0 | 0 | 95.3% |
| `config.py` | 51 | 39 | 12 | 0 | 0 | 0 | 76.5% |
| `context.py` | 137 | 137 | 0 | 0 | 0 | 0 | 100.0% |
| `generate_cv.py` | 504 | 407 | 93 | 0 | 4 | 0 | 80.8% |
| `generate_github_readme.py` | 320 | 267 | 53 | 0 | 0 | 0 | 83.4% |
| `generate_linkedin.py` | 285 | 242 | 43 | 0 | 0 | 0 | 84.9% |
| `generate_portfolio.py` | 137 | 109 | 28 | 0 | 0 | 0 | 79.6% |
| `icons.py` | 78 | 34 | 44 | 0 | 0 | 0 | 43.6% |
| `links.py` | 79 | 40 | 39 | 0 | 0 | 0 | 50.6% |
| `manifest.py` | 148 | 141 | 7 | 0 | 0 | 0 | 95.3% |
| `publish.py` | 274 | 265 | 9 | 0 | 0 | 0 | 96.7% |
| `publishers/filesystem.py` | 231 | 227 | 4 | 0 | 0 | 0 | 98.3% |
| `publishers/manual.py` | 69 | 66 | 3 | 0 | 0 | 0 | 95.7% |
| `registry.py` | 75 | 71 | 4 | 0 | 0 | 0 | 94.7% |
| `render.py` | 217 | 125 | 92 | 0 | 0 | 0 | 57.6% |
| `scaffold.py` | 52 | 45 | 7 | 0 | 0 | 0 | 86.5% |
| `secrets.py` | 51 | 51 | 0 | 0 | 0 | 0 | 100.0% |
| `utils.py` | 115 | 109 | 6 | 0 | 0 | 0 | 94.8% |
| `validate.py` | 204 | 197 | 7 | 0 | 0 | 0 | 96.6% |
| **Total** | 3691 | 3205 | 482 | 0 | 4 | 0 | 86.8% |

The work targeted the data-safety and error-handling modules: `cli`, `context`,
`manifest`, `publish`, `publishers/*`, `registry`, `scaffold`, `secrets`,
`utils` and `validate`. Their combined score went from 68.6% (1386 of 2020) to
96.1% (1942 of 2020). The generators, `render`, `icons`, `links` and `config`
were not targeted and are unchanged.

`context.py` deserves a note: the baseline killed 130 of its mutants, and a
later full run, with no change to `context.py` or its tests, killed 127. The
discovery tests move the process with `chdir`, so whether a mutant of the
explicit `cwd` argument was caught depended on where the test process stood.
`tests/test_mutation_context.py` pins discovery from a decoy working
directory, so those kills no longer depend on the process.

### Equivalent survivors

All 78 remaining survivors in the targeted modules are equivalent: no
observable behavior changes. They are listed by kind rather than tested.

| Count | Kind | Why it is equivalent |
|---:|---|---|
| 38 | `encoding="utf-8"` changed to `"UTF-8"`, `None`, or dropped | Same codec name; under the UTF-8 locale the runs use, the default is UTF-8 too. Only a non-UTF-8 locale would tell them apart. |
| 12 | argparse `type=Path` changed to `None` or dropped, `default=None` dropped | Every consumer wraps the value in `Path()` again; argparse's default is already `None`. |
| 8 | `False` changed to `None` (or a `check=False` dropped) | Only ever tested for truthiness; `subprocess.run` defaults `check` to `False`. |
| 4 | the type string inside `typing.cast` | `cast` does nothing at runtime. |
| 3 | `max(..., default=11)` changed | Unreachable: the table is printed only when at least one destination ran. The `default` was later removed when the header-width defect below was fixed. |
| 3 | `add_subparsers(dest=...)` changed or dropped | Nothing reads `args.command`. |
| 3 | the fallback passed to `_loaded()` in `validate.main` | Unreachable: each call sits behind a check that the file passed. |
| 2 | `_AdapterPublisher` initial `credentials` / `_cfg` | Always overwritten before use by `publish_destination` and `plan()`. |
| 2 | `ctx` passed to the built-in publishers' `publish()` | Neither built-in publisher reads it. |
| 2 | `cmd_list(None)`, `ini.set_defaults(init=True)` without `func=None` | `cmd_list` ignores its context; `func` already defaults to `None`. |
| 1 | `_SCHEMA_MAP.get(None, f"{stem}.schema.json")` | Every mapped name equals the fallback name. |

### Defects found

Two surviving mutants pointed at real defects. They are recorded as strict
`xfail` tests, not fixed, so the fix lands as its own change:

- `tests/test_mutation_manual.py::test_a_malformed_artifact_list_is_not_silently_ignored`:
  a manual destination whose `artifacts` is a string or holds a non-string is
  treated as declaring nothing, and reports `pending-manual` with an action
  asking a human to copy nothing.
- `tests/test_mutation_cli.py::test_publish_header_stays_separate_for_short_destination_names`:
  the publish table sizes its first column from destination names only, so
  when every name is shorter than `DESTINATION` the header reads
  `DESTINATIONSTATUS` and no longer lines up with the rows. Fixed afterwards: the
  column is now at least as wide as its header, and the test passes without
  the `xfail`.
