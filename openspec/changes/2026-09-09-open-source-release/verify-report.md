# Verification Report: 2026-09-09-open-source-release

**Branch / commit**: `feat/open-source-release` @ `ec30641`, tree clean before and after verification
**Mode**: Strict TDD (runner `uv run pytest -q`, threshold 80%), artifact store `openspec`
**Verdict**: **FAIL** (5 CRITICAL, 10 WARNING, 5 SUGGESTION). Status: `partial`.

> **Resolution (added after the report was written).** All five CRITICAL
> findings were closed in `195e440`, and the second-round review findings in
> the commit that follows it. The verdict below is the state at `ec30641` and
> is kept verbatim as the record of what verification found — it is not the
> current state of the tree. C2 (adapter idempotency), C4 (home paths in
> tracked content) and S1 (`Secret` pickling) were real defects; C3 was an
> incompletely implemented task marked done; C1 and C5 were the specs and the
> record disagreeing with settled decisions. Two findings were escalated to
> the owner rather than fixed: whether `projects.json` should be wrapped to
> carry an inline `schemaVersion`, and whether the publish-on-push
> requirement should be amended now that a CI filesystem write is known to be
> discarded.

`apply-progress.md` was treated as a claim. Everything below was re-run or re-observed.

## Completeness

| Item | Result |
|---|---|
| Tasks | 96/96 `[x]`, 0 unchecked |
| Requirements | 34 (4+3+2+2+7+3+3+5+5 across 9 specs) |
| Scenarios | 65 |

## Command evidence (observed this run)

| Command | Result |
|---|---|
| `uv run pytest -q --cov` | 336 passed in ~1.2s (apply-progress said 334); src coverage 92.88% (gate 80%) |
| same, inside `unshare -rn` (no network namespace) | 336 passed; `find -newer` found no modified files; `git status --ignored` byte-identical before and after |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 75 files already formatted |
| `uv run mypy` | Success, 21 source files |
| `uv run python -m profilekit.cli check` | "check passed: data valid, output/ up to date, destinations current" |
| `uv run pre-commit run --all-files` | all 14 hooks passed |
| `uv build` | sdist + wheel built; both contain `py.typed` and 7 schemas; wheel has no `generators/` or `generate_portfolio_data` |
| `pnpm install --frozen-lockfile --offline` + `pnpm build` (apps/portfolio) | succeeded, 5 routes |

Lowest-covered src modules: `icons.py` 74%, `links.py` 77%, `validate.py` 84%, `manual.py` 84%. All pre-existing or minor.

## Load-bearing claims, tested directly

| Claim | Verdict | Evidence |
|---|---|---|
| No generator writes outside its output dir | **Confirmed** | Ran `profile generate` under `bwrap` with `/` read-only and only `output/` writable: succeeded. Negative control with `output/` read-only failed on the first write. `registry.generators()` reads only the `profilekit.generators` group. |
| No publisher reachable from generate path | **Confirmed** | `cmd_generate` resolves only the generators group; distinct groups; test asserts implementation sets are disjoint. |
| `profile check` fails on a stale published destination | **Confirmed** | Overwrote `apps/portfolio/app/data/about.json` with `{}` in the real repo: `check` exit 1. Restored; tree clean. Same in a scaffolded project (drift, and never-published). `check` does not repair the destination. |
| Discovery never resolves to the installed package | **Confirmed** | No `__file__`-derived path in `src/` (only docstrings). Wheel installed in a fresh venv, run from an empty dir: `validate` and `check` exit 2 with "no profile.toml found ... run 'profile init'". |
| No real PII in `tests/**` | **Confirmed** | `test_no_real_pii.py` deny-list passes (7 markers, guard-the-guard present). Scaffold also clean under an independent `rg`. |
| Suite does not modify tracked files / no network | **Confirmed** | See the `unshare -rn` row. Caveat W6 on the guard's strength. |
| `manual` never reports `published` | **Confirmed** | Live `--execute` on a manual destination reported `pending-manual`; capability is fixed by kind, not configurable (test present). |
| `Secret` does not leak | **Confirmed for the stated channels**, one minor exception | `repr`, `str`, f-string, `%s`, `.format`, containers, `CredentialSet`, dataclass repr, logging, traceback and `capture_locals` traceback: all redacted. `pickle.dumps` does include the value (S1). |
| Scaffold has no maintainer identity; validates and generates | **Confirmed** | Independent `rg` for name/handle/email: none. Validates, generates six artifacts. Emits a non-fatal warning that `assets/pixel-mario.gif` is missing (S2). |
| Clean wheel install supports init -> validate -> generate -> check -> publish | **Confirmed** | Run end to end outside any checkout. With `filesystem` + `manual` destinations declared: dry-run writes nothing; `--execute` publishes, second run `unchanged`; drift makes `check` exit 1. |

## CRITICAL

**C1. Spec scenario "No config file present" is contradicted by the implementation.**
`project-configuration` says that with no `profile.toml` the tool "SHALL fall back to documented default relative paths under the current working directory". Implemented behaviour (and design D2: "no silent fallback to CWD") is exit 2. The code is coherent with the design and the owner's own expectation, but the spec was never amended, and there is no passing test for the spec's behaviour. Resolve by amending the spec scenario to exit 2, or implementing the fallback. Not satisfied as written.

**C2. Registry-adapter push destinations never republish changed content (verified bug in untested code).**
`publish._AdapterPublisher.plan()` returns a plan with no artifacts, so `plan_digest()` is the SHA-256 of empty input (`e3b0c442...`) for every run. Reproduced: v1 -> `published`; v2 (different content) -> `unchanged`, adapter called once. This is the only path that uses the ledger (filesystem reads its destination). It violates "Changed content is republished" for `push` destinations. `publish.py` lines 214-224 are uncovered, which is why 336 tests miss it. Also: `resolve()` returns the `CredentialSet` but `publish_destination` discards it, so adapters never receive the credentials the secrets module says the core injects. The filesystem path is correct and tested.

**C3. Output-contract requirements not met for the published JSON artifacts.**
(a) "Every JSON artifact emitted ... MUST include `schemaVersion`": `apps/portfolio/app/data/projects.json` is a bare array and carries none (deviation 2). (b) "Each emitted artifact type MUST have a corresponding JSON Schema ... documented, stable location": only `manifest.schema.json` is packaged for an emitted shape and documented in `docs/data-contract.md`. `about/social/skills/projects.schema.json` describe the canonical input; none mentions `schemaVersion`. The emitted files validate against them only because `additionalProperties` is true, which is accidental. A consumer cannot detect a version mismatch on `projects.json` without the manifest.

**C4. "No absolute developer paths" scenario fails literally, and R0 scenarios have no automated test.**
`git ls-files | xargs rg '/home/[a-z]+/'` matches 4 tracked files: `apply-progress.md`, the spec itself (documents the pattern), and two archived `archive-report.md` files with the owner's real home path. The spec says "no match SHALL be found". There is no test for this, for noise-path absence, for `.codegraph/` being ignored, or for the `cv/` workflow being absent. I confirmed noise paths, `.codegraph` ignore, and absent `render-cv.yml` by hand; those hold. Under the rule that a scenario is compliant only with a passing covering test, these are UNTESTED. The path scenario is FAILING in spirit and letter.

**C5. Strict TDD evidence is absent.**
`apply-progress.md` contains no "TDD Cycle Evidence" table (no RED/GREEN/TRIANGULATE/SAFETY NET columns) for any phase; phases 4-11 are a summary only. The strict module treats this as CRITICAL. Tests exist and pass, but RED-before-GREEN cannot be confirmed, and commits bundle tests with implementation.

## WARNING

- **W1. `profile-outputs` "exactly five artifacts"** now has six (`manifest.json`). Tests allow it; the spec text is stale and needs amendment.
- **W2. Publish workflow differs from spec and the difference is not in the recorded deviations.** Spec: run `profile publish` on push to `main`. Implemented: `publish.yml` runs `profile check` + a dry run on push; live publish only via manual dispatch. The rationale in the file is sound (a runner checkout is throwaway), but it is a fourth, undisclosed deviation. Path filter also includes `data/**`, `profile.toml` and the workflow file, wider than "output directory changed".
- **W3. Boundary test is weaker than the spec.** `GENERATOR_MODULES` is a hardcoded tuple (a second component list, and a new registered generator is not covered); "sandbox" is only `tmp_path`; there is no negative-control test for "catches an out-of-bounds write"; it calls `main(output_dir=)` rather than the registry path the CLI uses.
- **W4. Config keys differ from spec.** Spec names `output_dir`/`data_dir`/`schemas_dir`; implementation uses `[paths] output|data|schemas`. `output_dir = "..."` under `[paths]` is silently ignored and output goes to `output/` (reproduced).
- **W5. Design `accepts_schema` (D6) is not implemented**; no publisher rejects an out-of-range manifest version.
- **W6. Session guard is blind to some mutation.** It diffs `git status --porcelain --untracked-files=no`: a file already dirty that is modified further, or any untracked/ignored file written, goes unseen. The suite is clean today (independently verified), but the guard would not catch regressions of those kinds.
- **W7. Task 6.7 only partly done.** `cli.filesystem_destinations()` still reads `[publishers.*]` tables, and its docstring still says R7 will replace it. The blocking constraint (stale gate stays) is satisfied and tested; the registry rewiring the task names is not.
- **W8. `check` outside git has no freshness signal.** Design promised "degrade to manifest-hash comparison". `_manifest_is_valid` runs after regeneration, so it cannot detect staleness. The notice honestly says freshness was skipped, matching the spec.
- **W9. Coverage gap in review.** Phases 5-8 (test neutrality, registry, output contract, publication) never received an adversarial review. Phases 9-11 did (lineage `review-657dc538c1e7b69f`, approved, 21 advisory findings fixed in `ec30641`). C2 lives in phase 8, which is exactly the unreviewed range.
- **W10. Weak assertions.** `test_config.py:58` (`is not None`) is type-only; several `== []` asserts rely on companions. No tautologies or ghost loops found.

## SUGGESTION

- S1. `Secret` pickles its value; add `__reduce__` raising.
- S2. Scaffold's generated GitHub README references `assets/pixel-mario.gif`, which `init` does not create; `generate` warns.
- S3. `cmd_list` docstring says it lists publish destinations; it lists generators only.
- S4. Spec says `--live`; implementation uses `--execute` (spec says "e.g."). Align docs or spec once.
- S5. `cv.current_date` defaults to `auto`, not a frozen value; documented in `profile.toml`, fine, but spec says "today's values preserved".

## The three deliberate deviations

1. **`generatedAt` omitted: justified.** Spec requires only `schemaVersion`. A wall clock in a committed, diffed file breaks the byte-identical freshness guarantee; `test_manifest_is_byte_identical_across_runs` passes. Record it in design D6.
2. **`projects.json` stays an array: sound reasoning, but not yet justified against the spec.** It leaves a literal MUST unmet (C3). Either amend the requirement to exempt array artifacts and point them at the manifest, or wrap it and update the one consumer (it is in this monorepo).
3. **Registry order = sorted entry-point name: justified.** Spec is silent on order, generators are independent, goldens and `profile check` on the real repo show `output/` byte-identical, and `test_registry_order_is_stable` covers determinism.

## Known state, confirmed

- `data/social.json` `cvUrl` 404: owner data, left alone. Not verified here (network not used).
- `openspec/changes/2026-09-05-add-generator-cli` unarchived: out of scope.

## Compliance summary by spec

| Spec | Reqs | Status |
|---|---|---|
| monorepo-structure | 4 | Hygiene holds by manual check; absolute-path scenario fails (C4); no tests for 4 scenarios |
| generator-tooling | 3 | Compliant (pre-commit, PII neutrality, docs); W3 on the boundary |
| portfolio-data-sync | 2 | Compliant; W7 |
| profile-outputs | 2 | Compliant in behaviour; W1, W3, W4 |
| component-registry | 3 | Compliant |
| publication | 7 | Compliant for built-in kinds; C2 for adapters; W2 |
| output-data-contract | 3 | Not compliant (C3) |
| project-configuration | 5 | C1; W4 |
| package-distribution | 5 | Compliant (wheel/sdist, schemas, metadata, tag-gated release verified by test and inspection) |

Requirements fully satisfied with observed evidence: 28 of 34. Not satisfied (5): no-config-fallback (C1), content-hash idempotency for push (C2), schemaVersion on emitted artifacts and schema per artifact (C3, 2 requirements), absolute-path hygiene (C4), and a sixth, the publication-CI requirement, is met only in modified form (W2).

## Next step
Return to `sdd-apply` for C1-C5 (C1/C3/W1/W2 may be resolved by spec amendment by the owner). Do not archive.
