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
