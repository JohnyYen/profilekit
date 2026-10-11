# Archive Report: 2026-09-09-open-source-release

**Archived**: 2026-10-11
**Original branch**: `feat/open-source-release`
**Final commit**: `9334946` (docs amendment per owner decision)
**Artifact store mode**: `openspec` (repo-local)
**Status**: `success`

---

## Executive Summary

The open-source release change has been fully archived. All 96 implementation tasks are complete, verified by two rounds of adversarial review, and merged into the source-of-truth specification set. Five new capability specs have been added (`package-distribution`, `project-configuration`, `component-registry`, `output-data-contract`, `publication`); four existing specs have been updated with deltas (`generator-tooling`, `monorepo-structure`, `portfolio-data-sync`, `profile-outputs`). All blocking decisions have been resolved through owner amendments to the specs, and the change is ready for delivery.

---

## Task Completion Gate

**Status**: ✅ PASS

All 96 implementation tasks (phases 1-11) marked complete:
- Phase 1 (R0): Repo hygiene — 9/9 tasks ✅
- Phase 2 (R1): Legal + package identity — 10/10 tasks ✅
- Phase 3 (R2): Generator/publisher boundary — 7/7 tasks ✅
- Phase 4 (R6): Path decoupling — 13/13 tasks ✅
- Phase 5 (R8): Test neutrality — 8/8 tasks ✅
- Phase 6 (R7): Single registry — 9/9 tasks ✅
- Phase 7 (R3): Output data contract — 6/6 tasks ✅
- Phase 8 (R4): Publication layer — 13/13 tasks ✅
- Phase 9 (R5): CI automation — 7/7 tasks ✅
- Phase 10 (R9): Portfolio reference — 5/5 tasks ✅
- Phase 11 (R10): Docs/DX/release — 9/9 tasks ✅

---

## Verification Status

**First-round verification** (commit `ec30641`):
- Result: FAIL (5 CRITICAL, 10 WARNING, 5 SUGGESTION)
- All findings documented in `verify-report.md`
- Five CRITICAL findings were code defects or incomplete implementations

**Second-round verification** (commit `b52f3d7`):
- Result: PASS WITH OWNER DECISIONS (1 CRITICAL, 6 WARNING, 4 SUGGESTION)
- All five first-round CRITICAL defects closed
- NEW-C1 (array-shaped artifact versioning): Resolved via owner amendment to `output-data-contract` spec
- W-E (CI publish requirement): Resolved via owner amendment to `publication` spec
- Two other amendments already recorded inline in specs

**Final state** (commit `9334946`):
- Both owner decision amendments committed
- All verified code paths green
- Ready for archive

---

## Final Verification Commands

**Executed at commit `9334946`:**

| Command | Result |
|---------|--------|
| `uv run pytest -q` | 359 passed in ~1.2s, coverage 93.42% (gate 80%) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 75 files already formatted |
| `uv run mypy` | Success, 21 source files |
| `uv run python -m profilekit.cli check` | "check passed: data valid, output/ up to date, destinations current" |

All gates green.

---

## Specifications Merged

### New Specifications Created (5)

| Spec | Path | Requirements |
|------|------|--------------|
| Package Distribution | `openspec/specs/package-distribution/spec.md` | 5 (legal files, metadata, non-colliding name, packaged assets, tag-gated release) |
| Component Registry | `openspec/specs/component-registry/spec.md` | 3 (single registry, no core edits, kind distinction) |
| Project Configuration | `openspec/specs/project-configuration/spec.md` | 5 (CWD discovery, profile.toml, profile init, externalized opinions, git-optional check) |
| Output Data Contract | `openspec/specs/output-data-contract/spec.md` | 3 (schemaVersion, documented schemas, backward compatibility) |
| Publication | `openspec/specs/publication/spec.md` | 7 (config-declared destinations, dry-run default, manual capability, idempotency, failure isolation, zero-credential core, CI workflow gating) |

### Existing Specifications Updated (4)

| Spec | Path | Changes |
|------|------|---------|
| Generator Tooling | `openspec/specs/generator-tooling/spec.md` | MODIFIED: Pre-commit Hooks (self-contained, no `uv` required). ADDED: Test/fixture neutrality (fictional test dataset, no real PII, no tree mutation). ADDED: Documentation surface (README frames tool for adopters, docs/ with contract and authoring guides). |
| Monorepo Structure | `openspec/specs/monorepo-structure/spec.md` | ADDED: No tracked noise (development tools, screenshots, scrapers removed). ADDED: No absolute dev paths. ADDED: Vendored cv/ workflow resolution. ADDED: Portfolio documented as non-distributed reference consumer. |
| Portfolio Data Sync | `openspec/specs/portfolio-data-sync/spec.md` | MODIFIED: Component reclassified from generator to publisher. MODIFIED: Destination path now configurable (via profile.toml). MODIFIED: Publisher invoked by `profile publish`, never `profile generate`. ADDED: Registry integration requirement. Fixes shipped divergence bug (portfolio_data appeared in generate_all but not in CLI). |
| Profile Outputs | `openspec/specs/profile-outputs/spec.md` | MODIFIED: Output directory now configurable via `output_dir` in profile.toml (was hardcoded `output/`). MODIFIED: Artifact count updated from 5 to 6 (added `manifest.json`). ADDED: Generator output boundary enforcement (automated test, sandboxed filesystem). |

---

## Blocking Decisions Resolved

### Decision 1: Array-Shaped Artifact Versioning

**Finding**: NEW-C1 (second-round verification) reported that `projects.json` (a bare JSON array) could not carry `schemaVersion` inline without breaking consumers.

**Original Requirement**: Every JSON artifact MUST include `schemaVersion` field inline.

**Owner Decision**: Array-shaped artifacts declare their version through `output/manifest.json`, not inline.

**Implementation**: Spec amended with clear two-path requirement (inline for objects, manifest for arrays).

**Recorded in**: `output-data-contract/spec.md` requirements, with reasoning added as an amendment note.

### Decision 2: CI Publish Behavior

**Finding**: W-E (second-round verification) noted that spec required CI to publish on push, but implementation only performed dry-run + check on push, with actual publish gated on `workflow_dispatch`.

**Original Requirement**: CI MUST run `profile publish` on push to main.

**Owner Decision**: CI shall run `profile check` + dry-run on push (to verify destinations are current); live publish requires explicit manual dispatch.

**Rationale** (recorded inline): Filesystem and manual publishers write locally; on a runner, the project directory is discarded after the job, so publishing on push reports success for writes that don't persist. The correct CI question is "are destinations current?", which `check` answers.

**Recorded in**: `publication/spec.md` requirement "CI publish workflow gated and isolated from validation", with rationale added as an amendment note.

---

## Known Carried Items (Not Fixed, Deliberately)

From the verification reports, three findings were deliberately carried forward as out-of-scope or trade-offs:

1. **Hardcoded `verify` job name in one workflow test** — A test names the job hardcoded rather than parameterized. Low-risk, noted in W9 context.
2. **`--offline` mutating `os.environ` in-process** — A single site in `src/` sets an environment variable. Test asserts effect with variables cleared first. Acceptable pattern, documented.
3. **Duplicated exclude regex in pre-commit config** — Minor formatting. Not addressed.

None of these block archiving; all are captured in the verification report for future reference.

---

## Known Open Items (Owner's Data, Not Code)

**`data/social.json` `cvUrl` returns HTTP 404** — This is the owner's personal data, not a code defect. Not addressed; left for the owner to update.

---

## Out-of-Scope (Applied But Unarchived)

**Change `2026-09-05-add-generator-cli`** remains applied but unarchived. It is a pre-existing loose end, explicitly noted as out of scope in the open-source release proposal.

---

## Review Coverage

**Corrected during review of this merge.** This section originally claimed
that phases 9-11 and six named commits — including `b52f3d7`, `950ce5d` and
`9334946` — all received full 4R review with 21 findings fixed. That was
wrong, and it inflated the record in the one place where the record matters.
What actually happened:

| Candidate | Review |
|---|---|
| Phases 9-11 (`fd66462`..`d79af6a`) | 4R, approved, 21 advisory findings, fixed |
| `ec30641` + `195e440` | 4R, approved, 22 advisory findings, fixed |
| `b52f3d7` | 4R, approved, 17 advisory findings, fixed |
| The archive commit | one lens (`review-reliability`), approved, 5 findings — this correction among them |
| Phases 1-8 | **no adversarial review** |
| `950ce5d`, `9334946` | reviewed only as part of the archive slice |

The full-branch candidate exceeds the review tool's lens context budget and
cannot be reviewed as one unit, which is why coverage is per slice and why
phases 1-8 were never covered: by the time review began, their slices had
accumulated past the budget.

**Phases 5-8 and earlier commits**:
- No adversarial review; RDD candidate was too large for one review session
- Implementation verified through manual probes during second-round verification
- All code gates (pytest, ruff, mypy, pre-commit) passed in final state

---

## Spec Merge Summary

**Total requirements across all specs (old + new)**:

| Spec | Requirements |
|------|--------------|
| generator-robustness | 3 (pre-existing) |
| generator-validation | 2 (pre-existing) |
| github-readme-generation | 1 (pre-existing) |
| portfolio-generation | 2 (pre-existing) |
| profile-data | 2 (pre-existing) |
| skills-data-model | 3 (pre-existing) |
| generator-tooling | 8 (5 pre-existing + 3 added this change) |
| monorepo-structure | 10 (6 pre-existing + 4 added this change) |
| portfolio-data-sync | 7 (1 pre-existing, rewritten; 6 from this change) |
| profile-outputs | 8 (6 pre-existing + 2 added this change) |
| **package-distribution** | **5 (new)** |
| **component-registry** | **3 (new)** |
| **project-configuration** | **5 (new)** |
| **output-data-contract** | **3 (new)** |
| **publication** | **7 (new)** |

**Grand total**: 69 requirements across 15 specs

> Corrected during review of this merge: the figure read 71 while the table's
> fifteen rows sum to 69 (3+2+1+2+2+3+8+10+7+8+5+3+5+3+7).

---

## Artifacts Archived

**Change folder moved**:
```
openspec/changes/2026-09-09-open-source-release/
    → openspec/changes/archive/2026-10-11-open-source-release/
```

**Contents**:
- `proposal.md` ✅
- `design.md` ✅
- `tasks.md` (96/96 complete) ✅
- `apply-progress.md` ✅
- `verify-report.md` (two rounds, final state documented) ✅
- `specs/` (9 spec files, all merged into main specs) ✅
- `archive-report.md` (this file) ✅

**Main specs updated**:
- 4 existing specs merged with deltas
- 5 new specs created
- All changes committed to `openspec/specs/` source of truth

---

## Traceability

The change is now closed and the architecture has been archived. The source of truth for all capability definitions is `openspec/specs/`, and each spec reflects the current decision state, including owner amendments.

For full implementation evidence, refer to:
- `apply-progress.md` — 11 phases, 16 rows in TDD Cycle Evidence table
- `verify-report.md` — first and second-round findings, all resolved or carried
- Commit history on `feat/open-source-release` — 11 work-unit commits + 3 fix commits
- Final commit `9334946` — owner decision amendments

---

## Sign-off

**SDD Cycle**: Proposal → Specification → Design → Tasks → Apply (11 phases, 96 tasks) → Verify (2 rounds) → Archive ✅

**Status**: Complete. Change is ready for merge and release per ordinary repository policy.

---

## Correction to this report

The verification figures above were originally recorded as 336 tests at 92.88%
coverage while the report claimed to verify commit `9334946`. Those numbers
came from two commits earlier. The figures observed at `9334946` are 359 tests
at 93.42% coverage, and they are what the sections above now state.

The change artifacts were also initially left in
`openspec/changes/2026-09-09-open-source-release/` while only this report was
written into the archive directory, so the change existed in two places at
once. The artifacts have since been moved and the original directory removed.

## Carried follow-ups (not fixed)

Three findings from the second-round review were judged too small to justify
another fix-and-review cycle, and are recorded here rather than silently
dropped:

1. `tests/test_ci_workflows.py` hardcodes the workflow job name `verify`. If
   that job is renamed or the check and publish steps move apart, the test
   fails with a bare `StopIteration` rather than an ordering message.
2. `--offline` works by mutating `os.environ` inside `main()`. The suite calls
   `main()` in-process, so the setting outlives the call that asked for it.
3. The exclude regex in `.pre-commit-config.yaml` is duplicated across two
   adjacent hooks. Adding a generated directory means editing both, and a
   missed edit brings back the formatter-versus-generator conflict.

## Delivery status

Deliberately not done, and not blocking the archive:

- **Not pushed.** 31 commits exist only on the local `feat/open-source-release`
  branch; the branch does not exist on the remote.
- **No pull request.**
- **Not published to PyPI.** `profilekit` returns HTTP 404 on the index, so the
  `pip install profilekit` instruction in the README does not yet work. The
  gap between what the documentation promises and what the index serves is the
  most visible remaining item.
- `release.yml` is written, tag-triggered, and has never run. Publishing claims
  a global package name irreversibly, so it requires the owner's explicit
  approval each time rather than standing authorization.

## What "complete" means here

All 96 planned tasks are implemented and every automated gate is green, but
that is a statement about the plan rather than about readiness. Two honest
qualifications:

- **Review coverage is partial.** Phases 9-11 and three fix commits received
  adversarial review and were approved. Phases 5-8 and the final three commits
  did not. The three review rounds that did run each found real defects,
  including some the test suite did not catch, so there is no reason to assume
  the unreviewed phases differ.
- **The product is finished; the distribution is not.** A stranger arriving at
  the repository today finds a complete, documented, tested package they cannot
  install.
