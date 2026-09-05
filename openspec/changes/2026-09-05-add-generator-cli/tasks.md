# Tasks: Unified Generator CLI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–240 (new `cli.py` + `test_cli.py` + small config/doc edits) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Rollback boundary |
|------|------|-----------|----------------------|-------------------|
| 1 | `profile` CLI wrapping existing generators | PR 1 | `pytest -q tests/test_cli.py` | Revert commit; additive only |

---

## Phase 1: RED — failing CLI tests

- [x] 1.1 Create `tests/test_cli.py` importing `generators.cli as cli`; add a
      fixture/helper that monkeypatches `cli.GENERATORS` with spy callables
      recording call order, and monkeypatches `cli.validate.main` and
      `cli._git_output_is_clean`.
- [x] 1.2 Write test: `main([])` (no subcommand) returns non-zero and prints usage.
- [x] 1.3 Write test: `main(["generate"])` and `main(["generate","all"])` call every
      spy once in order `github-readme, linkedin, portfolio, cv`, return 0.
- [x] 1.4 Write test: `main(["generate","cv"])` calls only the `cv` spy, returns 0.
- [x] 1.5 Write test: `main(["generate","bogus"])` returns non-zero and error names the target.
- [x] 1.6 Write test: a spy raising `RuntimeError` makes `generate` return non-zero,
      message names the failing target.
- [x] 1.7 Write test: `main(["validate"])` returns the patched `validate.main` code (0 and 1 cases).
- [x] 1.8 Write test: `main(["check"])` returns 0 when validate=0 and git clean;
      non-zero when git dirty; non-zero and generators-not-run when validate!=0.
- [x] 1.9 Write test: `main(["list"])` prints all target names, returns 0.
- [x] 1.10 Write test: subcommand `--help` text contains no `--data-dir`/`--output-dir`.
- [x] 1.11 Run the suite; confirm `tests/test_cli.py` fails (module/functions absent) — RED.

## Phase 2: GREEN — implement `generators/cli.py`

- [x] 2.1 Create `generators/cli.py` with the `sys.path` bootstrap guard (mirroring
      `generate_all.py`) so script-mode import works.
- [x] 2.2 Import the four generator modules + `generators.validate`; define the
      insertion-ordered `GENERATORS` registry.
- [x] 2.3 Implement `_git_output_is_clean() -> bool` wrapping
      `subprocess.run(["git","diff","--exit-code","--","output/"])`.
- [x] 2.4 Implement `cmd_generate(target) -> int`, `cmd_validate() -> int`,
      `cmd_check() -> int`, `cmd_list() -> int` per design.
- [x] 2.5 Implement `build_parser()` (subparsers: generate[target], validate, check, list)
      and `main(argv=None) -> int` dispatch; `if __name__ == "__main__": sys.exit(main())`.
- [x] 2.6 Run `pytest -q tests/test_cli.py`; iterate to GREEN.

## Phase 3: Wiring, docs, and full gate

- [x] 3.1 `pyproject.toml`: add `[project.scripts] profile = "generators.cli:main"`
      and set `[tool.setuptools] packages = ["generators"]` (replace `py-modules = []`).
- [x] 3.2 Reinstall editable (`pip install -e .` in the venv); verify `profile list` resolves.
- [x] 3.3 `README.md`: document `profile` and `python -m generators.cli` usage
      (generate/validate/check/list); keep legacy invocations noted.
- [x] 3.4 Run full `pytest -q` (coverage ≥ 80%), `ruff check`, `ruff format --check`,
      `mypy generators/`; confirm all green.
- [x] 3.5 Sanity: `python -m generators.generate_all` and `python -m generators.cli check`
      both succeed and leave `output/` unchanged.

## Phase 4: CI integration

- [x] 4.1 `.github/workflows/validate.yml`: change "Validate data files" step to
      `uv run python -m generators.cli validate`.
- [x] 4.2 `.github/workflows/validate.yml`: change "Output freshness" step to
      `uv run python -m generators.cli generate` before `git diff --exit-code -- output/`.
- [x] 4.3 Add `generator-tooling` spec delta (freshness gate via CLI + CI validation via CLI).
- [x] 4.4 Verify locally with `uv run` under CI skip flags that both CLI steps succeed
      and leave `output/` unchanged.
