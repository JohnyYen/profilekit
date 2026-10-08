# Tasks: Open Source Release

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 3,000–6,000+ (13 relocated/created source modules, 25+ test files, full `pyproject.toml` rewrite, 5 legal/community docs, 3 authoring docs, 2 new CI workflows). The `src/profilekit` rename alone (`git mv` + import updates across ~20 existing test modules) is ~1,500+ lines with zero behavior change. |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 11 work units, one per R-phase (R0→R10) |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

The owner has pre-accepted `size:exception`: this lands as one PR, but each
work unit below is a self-contained commit with its own test command,
runtime harness, and rollback boundary — reviewable independently even
inside a single large diff.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|------------------|--------------------|
| R0 | Repo hygiene | Exception PR, commit 1 | `git ls-files \| rg -f noise-patterns.txt` (no match) | N/A — git/filesystem state only | Revert restores tracked noise; no behavior change |
| R1 | Legal + package rename | commit 2 | `uv run pytest -q` (full suite post-rename) | `pip install -e .` then `python -c "import profilekit"` | Mechanical rename, single commit, fully revertible |
| R2 | Generator/publisher boundary + `check` redefinition | commit 3 | `uv run pytest tests/test_output_boundary.py tests/test_filesystem_publisher.py tests/test_profile_check.py -q` | `profile check` against a mutated fixture (drift scenario) | Revert restores `generate_portfolio_data.py`; check reverts to git-diff-only |
| R6 | Path decoupling | commit 4 | `uv run pytest tests/test_context.py tests/test_config.py tests/test_init.py tests/test_check.py -q` | `profile init` in `tmp_path`; `profile generate all` from repo root, hash `output/` before/after | Revert restores `__file__` constants |
| R8 | Test neutrality | commit 5 | `uv run pytest tests/test_neutrality.py tests/test_golden.py tests/test_generate_all.py -q` | N/A — test-only change | Revert restores old fixtures/goldens; no production code touched |
| R7 | Single registry | commit 6 | `uv run pytest tests/test_registry.py -q` | `profile generate all` and `profile publish all`, diff outputs | Revert restores `cli.GENERATORS`/`generate_all.py` |
| R3 | Output data contract | commit 7 | `uv run pytest tests/test_manifest.py -q` | `profile generate all` then inspect `output/manifest.json` | Revert removes `schemaVersion`/manifest only |
| R4 | Publication layer | commit 8 | `uv run pytest tests/test_secrets.py tests/test_publish_cli.py tests/test_publishers_manual.py tests/test_publish_idempotency.py tests/test_publish_isolation.py tests/test_publish_zero_cred.py -q` | `profile publish all` (dry-run, zero credentials) against fixture project | Revert removes `profile publish`; generation/validation unaffected |
| R5 | CI automation | commit 9 | `uv run pytest tests/test_ci_publish_gate.py -q` | `workflow_dispatch` dry-run of `publish.yml` (or manual trigger on a fork) | Revert deletes `publish.yml`; `validate.yml` untouched |
| R9 | Portfolio reference docs | commit 10 | `uv run pytest tests/test_portfolio_docs.py -q` | `pnpm build` inside `apps/portfolio/` | Revert restores old README only |
| R10 | Docs/DX/release | commit 11 | `uv run pytest tests/test_precommit.py tests/test_readme.py tests/test_docs_surface.py tests/test_release.py -q` | `pre-commit run --all-files`; `pip install .` in a clean venv + `profile init` + `profile generate all` | Revert deletes `release.yml`/docs; no PyPI release has fired (tag-gated) |

### Carry-Forward Traceability

| Carry-forward | Tasks |
|---|---|
| `profile check` redefinition, same phase as reclassification | 3.5–3.7 |
| `test_generate_all.py` rewritten wholesale; `test_golden.py`/`test_monorepo_layout.py` repointed | 5.3–5.6 |
| R6 cutover byte-identical to today; `output/` unchanged proof | 4.12–4.13 |
| `profilekit` confirmed available on PyPI | 11.8 (no re-check) |
| Stale `openspec/config.yaml` `context:` fixed as R0 task | 1.9 |
| 3 `Applicable` threat-matrix rows → RED tests | 3.3 (row 1), 4.10 (rows 2–3) |
| Tests must not mutate the working tree | 5.5, 5.7 |

Threat-matrix rows marked `N/A` (push state, PR commands) intentionally have
no task — no git-push publisher or PR automation is introduced.

---

## Phase 1 (R0): Repo Hygiene

- [x] 1.1 RED: test asserting `git ls-files` excludes `.playwright-cli/`, `.agents/`, `.claude/skills/playwright-cli/`, `cv/.agents/`, tracked PNGs, `apps/portfolio/scripts/analyze-portfolio.js`. (Mechanical hygiene, no behavior — verified via `git ls-files | rg` runtime harness per the Review Workload Forecast's R0 row instead of a pytest RED test; see apply-progress for the exact command and output.)
- [x] 1.2 GREEN: `git rm -r --cached` the above, add `.gitignore` entries, delete `analyze-portfolio.js` from disk.
- [x] 1.3 RED: test grepping tracked files for `/home/johny` (fails on `apps/portfolio/.atl/skill-registry.md`, `cv/.atl/skill-registry.md`). (Same mechanical-hygiene exception as 1.1; verified via `git ls-files -z | xargs -0 rg -l '/home/johny'`.)
- [x] 1.4 GREEN: scrub or delete the absolute-path files above.
- [x] 1.5 RED: test asserting `cv/.github/workflows/render-cv.yml` cannot run (removed/disabled). (Same mechanical-hygiene exception; verified via file-absence check.)
- [x] 1.6 GREEN: remove or neutralize `cv/.github/workflows/render-cv.yml`; `cv/` content otherwise untouched.
- [x] 1.7 RED: test asserting `.codegraph/` is ignored, not untracked. (Same mechanical-hygiene exception; verified via `git status --short --ignored`.)
- [x] 1.8 GREEN: add `.codegraph/` to root `.gitignore`.
- [x] 1.9 Fix `openspec/config.yaml` `context:` block: remove the stale "no pyproject.toml/tests" claim and the "portfolio external" framing.

## Phase 2 (R1): Legal + Package Identity

- [x] 2.1 RED: test asserting `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md` exist and `LICENSE` names an OSI license.
- [x] 2.2 GREEN: author the five files (MIT for `LICENSE`).
- [x] 2.3 RED: test parsing `pyproject.toml` as PEP 621, asserting `description`/`readme`/`license`/`authors`/`keywords`/`classifiers`/`project.urls` non-empty.
- [x] 2.4 GREEN: fill `pyproject.toml` metadata.
- [x] 2.5 RED: test asserting no top-level `generators` module ships and `profilekit` imports.
- [x] 2.6 GREEN: create `src/profilekit/` (D4); `git mv` `generators/*.py` per the D4 file map; `[tool.setuptools.packages.find] where=["src"]`; retarget `--cov=`, mypy `files`, ruff `src`; drop `pythonpath=["."]`.
- [x] 2.7 Mechanical: update every `tests/**` import `generators.*` → `profilekit.*`; full suite (152 tests, 80% gate) is the sole acceptance gate — zero behavior change (D8).
- [x] 2.8 RED: `test_installed_package_finds_schemas` — `pip install .` into a venv outside the checkout; schema resolution fails today.
- [x] 2.9 GREEN: move `schemas/*.schema.json` into `src/profilekit/schemas/`; add `MANIFEST.in`, `py.typed`, `[tool.setuptools.package-data]`; load via `importlib.resources.files("profilekit.schemas")`.
- [x] 2.10 REFACTOR: remove the dead `sys.path` bootstrap in `cli.py`; confirm `uv run pytest -q` green.

## Phase 3 (R2): Generator/Publisher Boundary

- [ ] 3.1 RED: `test_all_generators_write_only_output_dir` — hash a sandboxed tmp tree before/after `generate all`; fails today (portfolio data writes outside it).
- [ ] 3.2 GREEN: parameterize every true generator's write path through an explicit `output_dir` argument.
- [ ] 3.3 RED (threat matrix row 1 — documentation-like paths): `test_destination_path_safety` — `../../etc`, `/tmp/x`, and a symlinked dir each rejected before any write.
- [ ] 3.4 GREEN: create `publishers/filesystem.py` with a path-safety guard (resolve under project root, reject absolute/`..`/symlink escapes), `plan()`/`publish()` writing the four portfolio JSON files; delete `generators/generate_portfolio_data.py`.
- [ ] 3.5 RED: `test_check_detects_app_data_drift` — mutate `data/about.json` in a fixture; `profile check` exits non-zero citing drift (fails today — `check` never runs the publisher).
- [ ] 3.6 GREEN: redefine `profile check` to run the filesystem publisher's `plan()` for `filesystem`-kind destinations, in addition to the existing git-diff gate (direct call — R7's registry finalizes discovery).
- [ ] 3.7 Cross-reference note: this closes the drift ungated today because `validate.yml:64` never invoked `portfolio_data`; R7 must not silently drop this gate when it rewires discovery.

## Phase 4 (R6): Decouple Paths

- [ ] 4.1 RED: `test_discovery_precedence` — flag > `PROFILEKIT_PROJECT` env > upward `profile.toml` walk > exit 2 with the documented message; nested and no-config cases.
- [ ] 4.2 GREEN: add `context.py` (`ProjectContext`, `discover_project()` per D2); symlink-resolved walk stops at `/`.
- [ ] 4.3 RED: `test_profile_toml_overrides_paths` — custom `output_dir` honored; unknown top-level key → `ConfigError`; unknown `[generators.X]` key passes through.
- [ ] 4.4 GREEN: add `config.py` parsing the D3 four-section `profile.toml`.
- [ ] 4.5 REFACTOR (mechanical, one commit): thread `ctx: ProjectContext` through `utils.py`, `cli.py`, `validate.py`, `generate_cv.py`, `generate_github_readme.py`, `generate_linkedin.py`, `generate_portfolio.py`; delete the `SCRIPT_DIR`/`ROOT_DIR`/`OUTPUT_DIR`/`DATA_DIR`/`SCHEMAS_DIR` constants (D2 table); switch monkeypatch tests to `ProjectContext`-over-`tmp_path`.
- [ ] 4.6 RED: `test_init_in_empty_directory` — `profile init` creates `profile.toml` + example `data/` with no maintainer name/email/handle.
- [ ] 4.7 GREEN: implement `profile init`.
- [ ] 4.8 RED: `test_externalized_opinions` — custom greeting renders; unset override reproduces today's exact default text.
- [ ] 4.9 GREEN: externalize `generate_github_readme.py:38,78,180` and `generate_cv.py:180,216-238` into `[generators.github-readme]`/`[generators.cv]`; replace frozen `current_date` with `"auto"` default; goldens pin it explicitly.
- [ ] 4.10 RED (threat matrix rows 2–3 — git repository selection, commit state): `test_check_degrades_without_git` — non-git tmp dir completes with the git check reported skipped, not failed; dirty/clean worktree still gates as before.
- [ ] 4.11 GREEN: rewrite the git invocation as `git -C <project_root> diff --exit-code -- <output_dir>` (argv list, never `shell=True`); degrade to manifest-hash comparison with a notice when `.git`/`git` is absent; read-only — no stage/commit/amend.
- [ ] 4.12 Commit a root `profile.toml` declaring `[paths]` and `[publishers.portfolio-data] destination = "apps/portfolio/app/data"` reproducing today's `__file__`-derived paths exactly.
- [ ] 4.13 Verification: hash `output/` before/after this phase's cutover; assert byte-identical; existing freshness gate stays green.

## Phase 5 (R8): Test Neutrality

- [ ] 5.1 RED: `test_no_real_pii_in_fixtures` — deny-list grep over `tests/**` for maintainer name/email/phone; fails today.
- [ ] 5.2 GREEN: create `tests/fixtures/project/` fictional persona; replace `tests/fixtures/portfolio_data/*.json` and username fixtures.
- [ ] 5.3 RED: rewritten `test_golden.py` asserting goldens read from `tests/fixtures/project/`, not `ROOT_DIR/data`; fails against current `:50-51,66,81,96,111`.
- [ ] 5.4 GREEN: repoint golden tests to the fixture project; regenerate golden files against fictional data.
- [ ] 5.5 RED: `tests/test_generate_all.py` rewritten wholesale — copy the fixture project into `tmp_path`, run with `cwd=tmp_path` + `PROFILEKIT_PROJECT`; assert the real `output/` and `apps/portfolio/app/data/` stay untouched.
- [ ] 5.6 GREEN: land the rewrite; delete the old body that mutates the real tree (`:25-53`).
- [ ] 5.7 GREEN: delete the `JohnyYen` invariant at `tests/test_monorepo_layout.py:59`.
- [ ] 5.8 Guard: assert zero tracked-tree diff after the full suite runs (generalizes 5.5's guard).

## Phase 6 (R7): Single Registry

- [ ] 6.1 RED: `test_single_source_enumerates_all` — fake entry points; `cli_targets() == registry.generators()`; fails while two lists exist.
- [ ] 6.2 GREEN: add `registry.py` reading `profilekit.generators`/`profilekit.publishers` via `importlib.metadata.entry_points(group=...)`.
- [ ] 6.3 RED: `test_new_component_needs_no_core_edit` — register a fake generator via entry point only; appears with no other file touched.
- [ ] 6.4 GREEN: delete `cli.py`'s `GENERATORS` dict and `generate_all.py`; `cmd_generate`/`cmd_list`/help derive from `registry.generators()`.
- [ ] 6.5 RED: `test_generate_excludes_publishers` and `test_unknown_kind_rejected` — `portfolio_data` MUST NOT run under `generate all`; an invalid-kind entry point is rejected at load.
- [ ] 6.6 GREEN: enforce kind-filtering in `registry.generators()`/`registry.publishers()`; raise `ConfigError` on unknown kind.
- [ ] 6.7 GREEN: register `portfolio_data` as a `profilekit.publishers` entry point; wire `[publishers.portfolio-data]` (4.12) through the registry, replacing R2's direct-call interim in `profile check`.
- [ ] 6.8 **Spec conflict — do not silently resolve by guesswork**: `portfolio-data-sync/spec.md`'s registration requirement scenario says `profile generate all` should write app data and log the step; this contradicts `component-registry/spec.md`'s explicit "generate does not invoke publishers" scenario and design D5. Implement per component-registry + D5 (generate excludes publishers; `profile publish all` includes `portfolio_data`); add a combined-flow test proving `generate all && publish all` reproduces the pre-change end state; flag the spec text for correction.
- [ ] 6.9 RED→GREEN: `test_divergence_regression` — both commands, from the same registry, produce identical sets for what they each own; no second list exists.

## Phase 7 (R3): Output Data Contract

- [ ] 7.1 RED: `test_json_artifacts_carry_schema_version` — every generated JSON artifact has top-level `schemaVersion`; fails today.
- [ ] 7.2 GREEN: add `manifest.py` (sha256 + `schemaVersion` per D6); inject the field into JSON-artifact generators; write `output/manifest.json` after a full run.
- [ ] 7.3 RED: `test_schema_resolves_and_validates` — a packaged schema file exists per `schemaVersion`; every artifact validates against it.
- [ ] 7.4 GREEN: add per-artifact JSON Schema files under `src/profilekit/schemas/`; wire validation into `profile check`.
- [ ] 7.5 RED: `test_additive_field_is_backward_compatible` and `test_breaking_change_bumps_major`.
- [ ] 7.6 GREEN: encode the D6 additive-vs-breaking rule as a reusable schema-diff test helper; stub `docs/data-contract.md` (expanded in R10).

## Phase 8 (R4): Publication Layer

- [ ] 8.1 RED: `test_secret_never_leaks` — `repr`/`str`/f-string/traceback of `Secret` never yield the value.
- [ ] 8.2 GREEN: add `secrets.py` (`Secret`, `CredentialSet`); core reads `[publishers.X.credential] env=NAME`, injects `Secret`s — publishers never call `os.environ`.
- [ ] 8.3 RED: `test_dry_run_default_no_writes` and `test_live_flag_required`.
- [ ] 8.4 GREEN: add `profile publish [dest|all]`; `Publisher` protocol (D7); dry-run default, `publish()` not called unless live.
- [ ] 8.5 RED: `test_manual_never_reports_success` — `manual` returns `pending-manual` with non-null `action_required`, never `published`.
- [ ] 8.6 GREEN: add `publishers/manual.py` and `publishers/base.py`.
- [ ] 8.7 RED: `test_unchanged_hash_skips_write` and `test_changed_hash_republishes`.
- [ ] 8.8 GREEN: idempotency ledger `.profilekit/publish-state.json` (gitignored) compared against manifest sha256 in `plan()`.
- [ ] 8.9 RED: `test_one_failure_does_not_abort_others`.
- [ ] 8.10 GREEN: wrap each destination's `plan()`/`publish()` in its own `try/except`; aggregate results; exit 1 iff any `failed`.
- [ ] 8.11 RED: `test_no_credentials_completes_without_fatal_error`.
- [ ] 8.12 GREEN: missing credential → `skipped` (exit 0) default; `--require-credentials` escalates to `failed`.
- [ ] 8.13 REFACTOR: verify core declares zero network dependencies in `pyproject.toml`; `filesystem`/`manual` remain stdlib-only.

## Phase 9 (R5): CI Automation

- [ ] 9.1 RED: `test_no_publish_without_output_change` — a diff touching only non-output paths does not trigger the publish job.
- [ ] 9.2 GREEN: add `.github/workflows/publish.yml` gated on `on.push.paths: ["output/**"]` to `main`.
- [ ] 9.3 RED: `test_missing_secret_skips_not_fails`.
- [ ] 9.4 GREEN: wire `profile publish all --live` in `publish.yml`; missing-credential skip (8.12) must not fail the job.
- [ ] 9.5 RED: `test_validate_workflow_never_publishes` — grep `validate.yml` for any publish invocation/credential env; none present.
- [ ] 9.6 GREEN: confirm `validate.yml` stays secret-free and publish-free; add the grep as a CI meta-test.
- [ ] 9.7 GREEN: add `workflow_dispatch` input to `publish.yml` defaulting to dry-run.

## Phase 10 (R9): Portfolio Reference Consumer

- [ ] 10.1 RED: `test_readme_describes_reference_role` — `apps/portfolio/README.md` states its reference-consumer role, not shipped with the package, no create-next-app boilerplate; fails today.
- [ ] 10.2 GREEN: rewrite `apps/portfolio/README.md`.
- [ ] 10.3 Verification: portfolio's existing build command still succeeds after 10.2 and the R0 hygiene pass.

## Phase 11 (R10): Docs, DX, Release

- [ ] 11.1 RED: `test_hooks_run_without_uv` — simulate a `pip`-only environment; hooks run successfully; fails today (`uv run` hooks).
- [ ] 11.2 GREEN: rewrite `.pre-commit-config.yaml` to use each tool's self-contained hook environment; add `pre-commit` as a dev dependency; document `pre-commit install`.
- [ ] 11.3 RED: `test_readme_frames_tool_for_adopters` — root `README.md` covers install/`profile init`/`generate`/`publish` before any maintainer-personal-data mention.
- [ ] 11.4 GREEN: reframe root `README.md`.
- [ ] 11.5 RED: `test_docs_dir_covers_contract_and_authoring`.
- [ ] 11.6 GREEN: write `docs/data-contract.md` (expand 7.6's stub), `docs/authoring-generators.md`, `docs/authoring-publishers.md`.
- [ ] 11.7 RED: `test_tag_triggers_release` and `test_push_to_main_does_not_release`.
- [ ] 11.8 GREEN: add `.github/workflows/release.yml`, tag-triggered only, TestPyPI dry-run before the real publish step. `profilekit` is confirmed available on PyPI (404 verified) — do not re-check.
- [ ] 11.9 Final verification: `uv run pytest -q` green, 80% coverage held; `pip install .` in a clean venv + `profile init` + `profile generate all` succeeds outside any checkout.
