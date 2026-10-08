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
