# Apply Progress: Open Source Release

## Phase 1 (R0): Repo Hygiene — COMPLETE

### Completed Tasks
- [x] 1.1 Noise-exclusion check (mechanical, see TDD Mode Note below)
- [x] 1.2 Untracked noise, added `.gitignore` entries, deleted `analyze-portfolio.js` from disk
- [x] 1.3 Absolute-path check (mechanical, see TDD Mode Note below)
- [x] 1.4 Scrubbed absolute-path files
- [x] 1.5 `cv/` workflow inert check (mechanical, see TDD Mode Note below)
- [x] 1.6 Removed `cv/.github/workflows/render-cv.yml`
- [x] 1.7 `.codegraph/` ignored check (mechanical, see TDD Mode Note below)
- [x] 1.8 Added `.codegraph/` to root `.gitignore`
- [x] 1.9 Fixed `openspec/config.yaml` `context:` block

### TDD Mode Note (explicit scope deviation, orchestrator-authorized)

Strict TDD Mode is active for this project, but the orchestrator's launch
instructions explicitly state: "Purely mechanical file moves and untracking
have no behavior to test — do not invent tests for them." Tasks 1.1, 1.3,
1.5, 1.7 are untracking/deletion/ignore-list changes with no code behavior,
so no pytest RED tests were written for them. Instead, each is verified by
the exact shell command from the tasks.md Review Workload Forecast's R0 row
(`git ls-files | rg ...`, no match) — see Work Unit Evidence below. The
existing 156-test pytest suite (no Python source touched this phase) was run
unchanged before and after to confirm zero regression.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `apps/portfolio/.playwright-cli/**` (47 files) | Untracked (`git rm --cached`) | Playwright CLI session logs/page dumps; still on disk, now gitignored |
| `apps/portfolio/.agents/**` (2 files) | Untracked | Agent-skill scaffolding (`frontend-design`) |
| `apps/portfolio/.claude/skills/playwright-cli/**` (8 files) | Untracked | Agent-skill scaffolding |
| `cv/.agents/**` (1 file) | Untracked | Agent-skill scaffolding inside vendored `cv/` subtree |
| `apps/portfolio/.atl/**` (4 files: 2 in portfolio, 2 in cv) | Untracked | Gentle AI skill-registry cache containing `/home/johny/...` absolute paths |
| `apps/portfolio/portfolio-{example,fixed,preview,starship}.png` (4 files) | Untracked | Manual-review screenshots |
| `apps/portfolio/scripts/analyze-portfolio.js` | Untracked + deleted from disk | Third-party site scraper; deleted outright per orchestrator instruction, not just gitignored |
| `cv/.github/workflows/render-cv.yml` | Deleted | Dormant workflow with `permissions: contents: write`; vendored subtree's own CI must not be capable of running from this repo |
| `.gitignore` (root) | Modified | Added `.codegraph/` and `cv/.agents/` entries |
| `apps/portfolio/.gitignore` | Modified | Added `.playwright-cli/`, `.agents/`, `.claude/skills/playwright-cli/`, `/portfolio-*.png` entries |
| `openspec/config.yaml` | Modified | Rewrote stale `context:` block: removed the false "no pyproject.toml/tests" claim (pyproject.toml and a 152+ test pytest suite exist, run via `uv run pytest -q`) and the "portfolio external" framing (`apps/portfolio/` is an in-monorepo consumer, not external) |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `git ls-files \| rg -i '\.playwright-cli/\|apps/portfolio/\.agents/\|apps/portfolio/\.claude/skills/playwright-cli\|cv/\.agents/\|portfolio-(example\|fixed\|preview\|starship)\.png\|analyze-portfolio\.js'` → no match (clean); `git ls-files -z \| xargs -0 rg -l '/home/johny'` restricted to non-`openspec/` tracked files → no match; `test -f cv/.github/workflows/render-cv.yml` → absent; `git status --short --ignored .codegraph` → `!! .codegraph/` (ignored, not untracked) |
| Runtime harness command/scenario and exact result | N/A — repo-hygiene/filesystem-state phase per the tasks.md Review Workload Forecast; no runtime boundary exists for untracking/ignoring files |
| Rollback boundary | A single commit; reverting restores the previously tracked noise files and the stale `openspec/config.yaml` text with zero behavior change (no Python source was touched) |

### Residual Finding (reported, not silently narrowed)

`git ls-files | rg '/home/johny'` — the literal completion-criterion command
— returns nothing, because `git ls-files` emits relative paths only; no
filename itself contains `/home/johny`. A deeper content-level check
(`git ls-files -z | xargs -0 rg -l '/home/johny'`) still matches 4 files,
all under `openspec/`:
- `openspec/changes/2026-09-09-open-source-release/tasks.md` and
  `specs/monorepo-structure/spec.md` — these are this very change's planning
  artifacts, which *document* the absolute-path pattern as an example/test
  description (task 1.3's own text names the pattern it expects the RED
  test to grep for). Scrubbing them would corrupt the planning record and
  is not named in R0's task list.
- Two pre-existing archived `archive-report.md` files from unrelated,
  already-merged changes (`2026-09-04-add-platform-specific-data-variety`,
  `2026-09-04-rich-github-readme`) — out of R0's scope; not touched.

These are self-referential SDD process docs, not production/source hygiene
violations, and are excluded from the `monorepo-structure` spec's practical
intent (the spec's own example text necessarily contains the pattern it is
describing). Flagging this explicitly rather than silently narrowing or
silently rewriting unrelated archived history.

### Deviations from Design
None — implementation matches design and tasks.md, with the one
orchestrator-authorized TDD-mode exception noted above (no invented tests
for mechanical untracking).

### Issues Found
None blocking. See Residual Finding above (informational only).

### Workload / PR Boundary
- Mode: `size:exception` (owner pre-accepted)
- Current work unit: R0 — Repo hygiene (work unit 1 of 11)
- Boundary: starts from clean `230e7d8`; ends with one commit covering all of Phase 1 (tasks 1.1–1.9)
- Estimated review budget impact: small relative to the overall exception — mostly deletions of already-noise files plus 3 modified lines-light files

### Status
9/9 Phase 1 tasks complete. Ready for next batch (Phase 2 / R1 — Legal + Package Identity) or `sdd-verify` if Phase 1 is reviewed standalone.

---

## Phase 2 (R1): Legal + Package Identity

### Completion
10/10 tasks complete (2.1–2.10).

### Execution Note
The delegated phase-2 agent terminated mid-run on a transient API
authentication error (HTTP 403) after completing the package rename but
before committing. The same failure had already killed a phase-1 attempt,
establishing a pattern rather than an accident. Recovery, on the product
owner's explicit instruction, was to commit the completed rename
immediately (`e5ee699`) to protect it from a third loss, and to close the
remaining gates inline in the orchestrator rather than relaunch a long-lived
sub-agent. `e5ee699` was therefore committed with `--no-verify` and with
known-failing ruff and mypy gates, disclosed in its own commit message; this
follow-up commit makes every gate green. No work was lost and no scope was
narrowed.

### What Changed
- `generators/` -> `src/profilekit/` (13 modules, `git mv`, history preserved).
- `schemas/*.schema.json` -> `src/profilekit/schemas/`, loaded via
  `importlib.resources.files("profilekit.schemas")`.
- `pyproject.toml`: distribution renamed to `profilekit`; full PEP 621
  metadata; `[tool.setuptools.packages.find] where=["src"]`;
  `[tool.setuptools.package-data]` ships `py.typed` and the schemas;
  `--cov`, mypy `files`, and ruff `src` retargeted; `pythonpath=["."]` dropped.
- Two console scripts: `profile` and `profilekit`.
- Added `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `CHANGELOG.md`, `MANIFEST.in`, `src/profilekit/py.typed`.
- Removed the dead `sys.path` bootstrap from `cli.py` (2.10).
- Three new test modules: `test_legal_files.py`, `test_package_metadata.py`,
  `test_package_name.py`.

### Latent Bug Surfaced by the Rename
`importlib.resources.files()` returns a `Traversable`, not a `Path`.
`validate.py` called `.exists()` on it (absent from the protocol) and passed
it to a `Path`-typed `_load_json`. Fixed properly rather than suppressed:
`_load_json` now accepts `Traversable | Path` and reads via `.read_text()`,
and the existence check uses `.is_file()`. A `type: ignore` would have left a
real defect in place behind a silenced diagnostic.

### Test Strengthening
Two `zip()` calls in `tests/test_generate_portfolio_data.py` gained
`strict=True`. Both tests assume 1:1 correspondence; without `strict` a
length mismatch would truncate silently and the assertion would pass.

### Exit Gate Evidence
- `uv run pytest -q`: 164 passed, coverage 86.52% (gate 80%).
- Coverage measured `--cov=profilekit`, and the report names 13 modules under
  `src/profilekit/` totalling 779 statements — not a vacuous 0% or 100%.
- `uv run ruff check .`: All checks passed.
- `uv run ruff format --check .`: 47 files already formatted.
- `uv run mypy`: Success, no issues in 13 source files.
- `uv build`: wheel + sdist built. Wheel contains all 6
  `profilekit/schemas/*.schema.json` plus `profilekit/py.typed`.
- Install smoke test in a venv outside the checkout: both `profile` and
  `profilekit` console scripts resolve; all 6 schemas enumerate and read via
  `importlib.resources`; `profile list` runs.

### Name Consistency
`pyproject.toml` (`name`, scripts, `where`, `package-data`), the real
directory `src/profilekit/`, and `CONTRIBUTING.md` / `CHANGELOG.md` /
`SECURITY.md` all state `profilekit`. `LICENSE` and `CODE_OF_CONDUCT.md`
intentionally do not name the package — neither document type does.

### Carried Forward (not phase-2 scope)
- `cli.py` still comments that its `GENERATORS` dict is the "single source of
  truth" while `generate_all.py` keeps a parallel list. The comment remains
  false and the divergence bug remains live: `profile list` still omits
  `portfolio_data`. Both are R7's job (Phase 6).
- `generate_all.py` retains a `sys.path` bootstrap; that module is deleted in
  R7.
- Path resolution is still repo-relative (`ROOT_DIR = parent.parent.parent`),
  so an installed CLI outside a checkout cannot find `data/`. That is R6
  (Phase 4) by design; only schema resolution was decoupled in this phase.

### Workload / PR Boundary
- Mode: `size:exception` (owner pre-accepted)
- Work unit: R1 — Legal + Package Identity (work unit 2 of 11)
- Boundary: `15418f7` -> `e5ee699` (rename, gates red) -> this commit (gates green)

### Status
10/10 Phase 2 tasks complete, all gates green. Next: Phase 3 (R2 — the
generator/publisher boundary), blocked pending authentication recovery before
sub-agent delegation resumes.

---

## Phase 3 (R2): Generator/Publisher Boundary

### Completion
7/7 tasks complete (3.1–3.7).

### Execution Note
Three consecutive delegated attempts at this phase produced nothing: two died
on `HTTP 403 authentication_failed` and one when the host process exited, each
time before any commit. Disk verification after each death confirmed zero
commits past the phase baseline and all seven tasks still unchecked.

The fourth attempt was executed inline by the orchestrator in three committed
increments rather than delegated a fourth time. Long-lived sub-agents are the
failure mode here, so the work was sized to survive one.

### What Changed

**3.1–3.2 (`35c357d`) — the output directory is caller-owned.**
Every generator's `main()` now takes an explicit `output_dir`, defaulting to
the module-level `OUTPUT_DIR`. A generator writing to a fixed module constant
cannot be redirected, which makes the boundary unenforceable and the write
path untestable without monkeypatching private state.
`tests/test_generator_output_boundary.py` asserts each generator accepts the
argument, that running all four leaves no file outside the directory they were
given, and that no publisher module is reachable from the generate path.

**3.3–3.4 (`fe7a848`) — the filesystem publisher is extracted.**
Added `profilekit.publishers` with design D7's capability model (`push` vs
`manual`, where `manual` reports `pending-manual` and may never report
`published`) and a plan/publish split so a dry run computes drift without
writing. Added `FilesystemPublisher`, carrying the four canonical JSON shapes
to a configurable destination, with `resolve_destination()` rejecting absolute
paths, parent-directory escapes, and symlink escapes *before* any content is
produced. Re-publishing identical content reports `unchanged`.
Deleted `generate_portfolio_data` and unwired it from `generate_all`; its
transform tests moved to `tests/test_publisher_transforms.py`, keeping the
missing-canonical-file case that must abort before producing a partial set.

**3.5–3.6 — `profile check` now gates published destinations.**
`cmd_check` runs `_stale_published_destinations()`, which calls each
filesystem destination's `plan()` and fails naming what drifted. It is a dry
run by construction: repairing the destination here would hide the exact
problem the gate exists to surface, and a test asserts it does not.

**3.7 — the constraint is recorded where R7 will read it.**
Task 6.7 in `tasks.md` now carries a blocking constraint spelling out that
this gate is the only thing covering `apps/portfolio/app/data/`, and that
replacing `cli.FILESYSTEM_DESTINATIONS` with registry discovery must carry
`_stale_published_destinations()` forward.

### Why 3.6 Was Load-Bearing
Reclassifying `portfolio_data` as a publisher removes it from the generate
path. `.github/workflows/validate.yml:64` only diffs `output/`, and never
invoked `portfolio_data` even before this change — that was the shipped
divergence bug. So after the reclassification, `profile check` is the only
thing that looks at the destination at all. Had 3.6 been deferred to a later
phase, destination drift would have ended up *less* protected than before the
refactor.

### Exit Gate Evidence
- `uv run pytest -q`: 176 passed, coverage 87.92% (gate 80%).
- Coverage reports 14 modules under `src/profilekit/`; both new publisher
  modules at 100%.
- `uv run ruff check .`: All checks passed.
- `uv run ruff format --check .`: 51 files already formatted.
- `uv run mypy`: Success, no issues in 14 source files.
- `uv build`: wheel contains `profilekit/publishers/{__init__,filesystem}.py`
  and no longer contains `generate_portfolio_data`.
- `python -m profilekit.cli check` against the live repo: exit 0 —
  "data valid, output/ up to date, destinations current". The real
  `apps/portfolio/app/data/` is current, and the gate now verifies it.

### Carried Forward (not Phase 3 scope)
- Path resolution is still repo-relative (`parent.parent.parent`). R6 (Phase 4).
- `cli.FILESYSTEM_DESTINATIONS` is a literal interim, as task 3.6 specifies,
  because R7 finalizes discovery. The `cli.GENERATORS` comment was narrowed to
  say what it actually covers instead of claiming to be the single source of
  truth while `generate_all` keeps a parallel list. R7 (Phase 6) collapses both.
- `generate_all.py` retains its `sys.path` bootstrap; deleted in R7.
- `tests/test_generate_all.py` still writes to the real `output/`. R8 (Phase 5).
- `profile publish` does not exist yet; `FilesystemPublisher` is reachable from
  `check` by direct call only. The CLI surface is R4 (Phase 8).

### Workload / PR Boundary
- Mode: `size:exception` (owner pre-accepted)
- Work unit: R2 — Generator/Publisher Boundary (work unit 3 of 11)
- Boundary: `da3799a` -> `35c357d` -> `fe7a848` -> this commit

### Status
7/7 Phase 3 tasks complete, all gates green. Next: Phase 4 (R6 — path
decoupling, `profile.toml`, `profile init`), 13 tasks.
