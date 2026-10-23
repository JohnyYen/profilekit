# Review phases 1-8 and add phase 12 e2e tests

Locator: `odd/tasks/review-phases-1-8-and-e2e.md` · Engram mirror: `odd/review-phases-1-8-and-e2e/tasks`

## Objective
Close the review-coverage gap of the archived `open-source-release` change (phases 1-8 were never
reviewed as slices, except a partial phase 4) and extend the end-to-end suite (phase 12).

## Why
Every review round that ran on this branch found real defects, including some the test suite missed.
Unreviewed phases cannot be read as equivalent to reviewed ones.

## Constraints
- The full branch exceeds the native lens context budget; review runs per phase slice only.
- `--base-ref` reviews base..HEAD, so each historical slice is reviewed in its own detached
  worktree at the phase's last commit: `../profile-data-worktrees/review-pN`.
- Findings are checked against the current `feat/open-source-release` HEAD before any fix: later fix
  commits may already have closed them. Fixes land as forward commits on the feature branch.
- Consent is per candidate; each medium/high slice relays its own consent envelope.
- Push, PR and PyPI publishing stay with the owner.

## Slices (base -> head, assessed risk, authored lines)
| Phase | Base | Head | Risk | Lines |
|-------|------|------|------|-------|
| 1 (R0) | 230e7d8 | 15418f7 | high | 3435 |
| 2 (R1) | 15418f7 | da3799a | high | 4326 |
| 3 (R2) | da3799a | 09f0bad | high | 1360 |
| 4 (R6) | 09f0bad | 914f3e5 | high | 2307 |
| 5 (R8) | 914f3e5 | d091141 | medium (slice budget) | 1106 |
| 6 (R7) | d091141 | 03cc786 | high | 689 |
| 7 (R3) | 03cc786 | 4c465e9 | high | 806 |
| 8 (R4) | 4c465e9 | fd66462 | high | 1073 |

## Tasks
Route: review tasks are inline (native lifecycle commands); fix and e2e writes route per the
writer trigger (2+ non-trivial files -> delegated writer).

- [x] T1 Review phase 1 slice — STOPPED `lens_context_budget_exceeded` (74 files, single commit
      `e702db5` that is ~97% deletions of untracked noise; cannot be split without rewriting history).
      Consent granted, no authority created. Not natively reviewable.
- [x] T2 Review phase 2 slice — granted, 4 lenses, approved, burned (`review-83d5a3f612916c3f`); 10 warnings
- [x] T3 Review phase 3 slice — granted, 4 lenses, approved, burned (`review-1f2bd81c898d28bc`); 9 warnings
- [x] T4 Review phase 4 slice — granted, 4 lenses, 2 CRITICAL (init clobbers existing data/*.json);
      one bounded correction (27 lines) validated, approved, burned (`review-b4eebb497babb70f`).
      Fix ported to HEAD test-first (RED observed): commit `2db9195`.
- [x] T5 Review phase 5 slice — granted, 1 lens (medium), approved, burned (`review-1a7b63a0b615d07e`); 3 warnings
- [x] T6 Review phase 6 slice — granted, 4 lenses, approved, burned (`review-95387c58f5f5fa29`); 11 warnings
- [x] T7 Review phase 7 slice — granted, 4 lenses, approved, burned (`review-f7c41bfff487cdc8`); 13 warnings
- [x] T8 Review phase 8 slice — granted, 4 lenses, approved, burned (`review-9ffee9f2d4ffff5d`); 13 warnings
- [x] T9 Fix every confirmed defect, in order, one commit each (owner decision 2026-10-20: all of them).
      Triage: 33 still present, 14 fixed, 5 obsolete, 3 disputed; plus 3 e2e strict xfails.
  - [x] D1 (`0228449`, RED 7 failing -> GREEN) filesystem publisher accepts the project root, data/ or output/ as destination (overwrites canonical data)
  - [x] D2 (`d2de5da`, RED 3 failing -> GREEN) per-file symlink escape in the filesystem publisher (`write_text` follows symlinks)
  - [x] D3 (`f3f0790`, RED 4 failing -> GREEN) empty generator registry: `generate all` writes only the manifest and exits 0; `list` exits 0
  - [x] D4 (`c4f8ba2`, RED traceback -> GREEN) publish ledger write: results table lost on write failure; write not atomic
  - [x] D5 (`03e0202`, RED UnicodeDecodeError/PermissionError -> GREEN) publish ledger read: UnicodeDecodeError/OSError escape before the destination loop
  - [x] D6 (`e339b3e`, RED JSONDecodeError traceback -> GREEN, xfail removed) validate crashes with a traceback on malformed skills/projects/social JSON (e2e xfail)
  - [x] D7 (`5809780`, RED unnamed file -> GREEN, xfail removed) generate does not name the malformed data file (e2e xfail)
  - [x] D8 (`7f432ff`, RED 12 failing -> GREEN, last xfail removed; e2e 49 passed) contract: manifest carries no version for the published projects.json (e2e xfail).
        Owner decision 2026-10-20: the filesystem publisher writes a manifest.json into the destination
        (schemaVersion + per-file version and digest), with its own schema, validation and docs.
  - [x] D9 (`ffa211a`, RED 3 -> GREEN) duplicate entry-point names silently shadow each other
  - [x] D10 (`8d6dff8`, RED 3 -> GREEN; e2e plugin contract: `list` no longer fails on a broken plugin) eager plugin loading: one broken entry point breaks every generate/list
  - [x] D11 (`edd9157`, RED -> GREEN; hidden files skipped, unknown names still indexed for plugins; dead digest branch removed) manifest indexes stray files (dotfiles, unknown names); unreachable digest-mismatch branch in check
  - [x] D12 (`6272f22`, RED floor 61 < 77 -> GREEN; wheel builds) setuptools>=61 floor with PEP 639 `license = "MIT"` (needs >=77)
  - [x] D13 (`6935c77`, RED ImportError/exit 0 -> GREEN; exit 2 config error) malformed credential declaration treated as missing credential (skipped, exit 0)
  - [x] D14 (`2000cf1`, RED 4 -> GREEN; dry-run push now `would-publish`, linkedin -> pending-manual) `skipped` overloaded for dry-run and missing credential; linkedin adapter labelled capability push
  - [x] D15 (`b5fce22` `9d7566a` `70c0aca` `12ca7a6` `da189e0` `700785a`; each RED shown by a reverted src mutation; 426 passed) unit-test gaps: pipeline return codes and .json coverage, per-generator file sets, manual in env guard,
        stderr asserts in contract-version tests, generators-namespace test env dependence, conftest guard ignores untracked
  - [x] D16 (`54012b3` `c97ff0b` `4329338` `f0d80c7`; cmd_list docstring already fixed by D10) docs/wording: SECURITY.md archive path and PyPI line, publish_destination docstring, idempotency claim,
        projects.json version claim, "authoritative index", cmd_list docstring, `_manifest_is_valid` name,
        dead `portfolio-data` publisher entry point
- [x] T10 Phase 12: map e2e gaps against `tests/e2e/test_adopter_journey.py` — delegated explorer; 13 gaps
- [x] T11 Phase 12: implement the new e2e tests — delegated writer; `bded622`: 46 passed, 3 strict xfail
      (validate traceback on malformed skills/projects/social JSON; generate omits the malformed file name;
      manifest has no projects.json version entry). RED not applicable: behavior pre-existed.
      Parent spot check: `pytest tests/e2e --no-cov` 46 passed, 3 xfailed. RDD assess 4d80fa3..HEAD: high, due.
- [x] T12 Close: 426 unit passed (94.56%), 51 e2e passed, ruff/format/mypy clean, pre-commit 13 passed
      + 1 skipped (no files); review worktrees removed

## Acceptance criteria
- Every slice 1-8 reaches a terminal review outcome (approved, declined, or a recorded stop reason).
- Every candidate-caused severe finding is either fixed at HEAD with a test, or recorded as already
  fixed with the commit that fixed it.
- New e2e tests pass from an installed wheel, outside any checkout.

## Progress
- Worktrees created for all eight slices; all eight assessed `review_due: true`.
- T1-T8 terminal. 55 non-blocking warnings (+34 suggestions) collected; triage against HEAD delegated
  to a read-only explorer (T9). Phase 12 gap mapping delegated in parallel (T10).
- `2db9195` fix(init): full suite 385 passed, coverage 93.43%, pre-commit green.
- 4d80fa3..e29f1bc reviewed: medium, 1 lens, approved, burned (`review-9d56d888e00d5b6c`). Boundary -> e29f1bc.
- Full-branch candidate (stop hook): consent granted twice, START failed `lens_context_budget_exceeded`
  (280 files / 21k lines, not_started). Third confirmation that the branch is reviewable only by slice.
- e29f1bc..5809780 (D1-D7) reviewed: medium, 1 lens, approved, burned (`review-cbc99daea5be0228`). Boundary -> 5809780.
  Suite 388 passed, e2e 48 + 1 xfail (D8).

- ee39bdc..f558ef8 (D8 review burned `review-f113004d7aaa3598` covered ..ee39bdc; D9-D11 slice: owner
  declined review, `declined_this_candidate`). Next slice base: f558ef8.

- 2026-10-23: owner turned review OFF for this clone (`gentle-ai review mode disable --scope clone`).
  No further slice reviews; delivery follows ordinary repository policy (disabled/unmanaged).

## Next step
Feature complete. Open, owner-owned: push and PR; PyPI release; README `pip install profilekit` is only
true after the first release; `data/social.json` cvUrl 404 (pre-existing). Phase 1 (`e702db5`) stays
natively unreviewable; D9-D16 were not reviewed (owner declined D9-D11, then turned review off).
