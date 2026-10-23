# Quality hardening: remove the causes behind the defect history

Locator: `odd/tasks/quality-hardening.md` · Engram mirror: `odd/quality-hardening/tasks`

## Objective
Every review round on this branch found real defects. They cluster into four classes: unguarded
destructive writes, unhandled errors, shape-asserting tests, and docs that describe behavior the
code does not have. Fix each class structurally so a new instance cannot land unnoticed.

## Constraints
- Owner decision 2026-10-23: one agent per solution, in parallel, without collisions.
- Each writer works in its own worktree and branch from base `054bb9e`
  (`../profile-data-worktrees/<name>`, branch `quality/<name>`). The parent integrates the branches
  into `feat/open-source-release` in a fixed order and resolves conflicts.
- Review mode (RDD) is OFF for this clone; Q4 is an independent read-only review, not RDD.
- Push, PR and PyPI stay with the owner.

## Tasks (route: delegated, one writer per worktree; Q4 read-only)
- [x] Q1 Mutation testing baseline (`mutmut`), plus new tests that kill surviving mutants
      (worktree `mutation`; new test files only, no src changes). Integrated as 12 commits ending `7eab087`
      + `6764b05` (two ledger tests re-pinned through safe_io after Q2). Score 71.8% -> 86.8% overall,
      68.6% -> 96.1% in targeted modules; 78 equivalent mutants documented in docs/quality/mutation-baseline.md.
      Two strict xfails = defects for Q6: malformed manual `artifacts` silently ignored; short-name
      publish header merges (same as F3). After integration: 645 unit + 3 xfail (97.05%), 51 e2e.
- [x] Q2 Single safe-write helper for every file write in src, enforced by an AST architecture test
      (worktree `safe-write`). Integrated as `2dd0bb4` `a654a4d` `be7c20b`: 6 write sites / 8 raw calls migrated,
      RED ImportError -> 22 tests GREEN, architecture test proven by a reverted raw write. Known gap:
      `Path.replace` is indistinguishable from `str.replace` in the AST scan (documented). 496 unit passed.
- [x] Q3 mypy `strict` + ruff `BLE`, `S`, `TRY` rule sets, code brought into compliance
      (worktree `strict-lint`). Integrated as `2bb971f` `ae88790` `056482a` `f5fd2fe` `d62d729` (2 import
      conflicts with Q2 in publish.py resolved by hand). 52 mypy errors fixed; TRY003 ignored globally
      (messages carry context); 2 real defects fixed test-first: load_json_strict returned scalars;
      scheme-less/`file:` URLs crashed validate or read local files. After integration: mypy strict clean,
      ruff clean, 506 unit (94.87%), 51 e2e, pre-commit green.
- [x] Q4 Independent read-only review of the unreviewed surface: fixes D9-D16 (ee39bdc..4a489dc) and
      phase 1 (`e702db5`, insertions only); findings only. Result: 0 CRITICAL, 2 WARNING, 5 SUGGESTION,
      no regression from a fix. To fix in Q6:
  - [ ] F1 WARNING non-table `[publishers]` entry silently dropped -> publish exits 0 (context.py, config.py)
  - [ ] F2 WARNING unanchored `lib/` in .gitignore hides new files under apps/portfolio/app/lib/
  - [ ] F3 publish table header runs together when destination names are short (cli.py)
  - [ ] F4 manifest.build follows symlinks in output/ (manifest.py), unlike the publisher
  - [ ] F5 plugin publisher named `filesystem`/`manual` silently shadowed by built-ins (publish.py)
  - [ ] F6 stale openspec/config.yaml context (old layout, hard-coded test count)
  - [ ] F7 validate.yml / portfolio.yml declare no `permissions:`
  - [ ] F8 (Q1 xfail) manual destination with malformed `artifacts` reports pending-manual for nothing
- [x] Q5 Docs-to-code coherence test: commands, flags, statuses and paths named in README/docs
      exist in the CLI (worktree `docs-coherence`). Integrated as `c762129` + `c8b1242` (12 tests; each check
      proven to fail on a bogus claim; fixed the undocumented `failed` status). 438 unit passed.
- [ ] Q6 Integrate in order Q1 -> Q5 -> Q2 -> Q3, then fix confirmed Q4 findings; full checks;
      remove worktrees

## Acceptance criteria
- Mutation score measured and recorded, before and after Q1's new tests.
- No direct file write in src outside the safe-write helper (architecture test fails otherwise).
- `mypy --strict` and the extended ruff rule sets pass on src.
- A docs claim naming a nonexistent command/flag/status fails a test.
- Every Q4 finding is fixed with a test, or recorded as disputed with a reason.

## Progress
- Base `4a489dc`: 426 unit (94.56% line, 93.36% branch), 51 e2e, ruff/mypy (non-strict) clean.

## Next step
Launch Q1-Q5 in parallel.
