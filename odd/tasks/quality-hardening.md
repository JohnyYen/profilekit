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
- [ ] Q1 Mutation testing baseline (`mutmut`), plus new tests that kill surviving mutants
      (worktree `mutation`; new test files only, no src changes)
- [ ] Q2 Single safe-write helper for every file write in src, enforced by an AST architecture test
      (worktree `safe-write`)
- [ ] Q3 mypy `strict` + ruff `BLE`, `S`, `TRY` rule sets, code brought into compliance
      (worktree `strict-lint`)
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
- [ ] Q5 Docs-to-code coherence test: commands, flags, statuses and paths named in README/docs
      exist in the CLI (worktree `docs-coherence`)
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
