# Proposal: Harden the Profile Generator Pipeline

## Intent

The generator pipeline works for the happy path but is fragile and under-guarded. CI runs only `validate.py`, so the 76-test suite never runs — the TDD safety net is invisible to CI. Validation is 225 lines of hand-rolled logic that never enforces `schemas/*.schema.json` (object shapes, dates, URLs, `oneOf` slip through). Generators emit raw tracebacks on bad data, `generate_all.py` breaks as a plain script, `whatIBuildVariants` is dead data no generator reads, and experience/education/date formatting is duplicated across three generators. Icons load from external services with no reachability check. This change hardens correctness, robustness, and quality without changing rendered output for existing data.

## Scope

### In Scope
- **T1 Correctness**: (1) CI runs `pytest` (install deps + run suite in `validate.yml`). (2) `generate_all.py` runs as plain script AND module. (3) Migrate `validate.py` to `jsonschema` so `schemas/*` are authoritative (object/`oneOf`/required); add `jsonschema` to `pyproject`; keep per-file PASS/FAIL, non-zero exit, and the `validate_portfolio_highlights` cross-field warning.
- **T2 Robustness**: (4) Graceful error handling in all generators (missing file/field, malformed JSON → clear "which file, which field" message + non-zero exit, no traceback). (5) Icon reachability check (in validate or a helper) that warns on unresolved skillicons slug / iconUrl.
- **T3 Quality**: (6) Wire `whatIBuildVariants[<platform>]` (github/linkedin/cv/portfolio) with fallback to `whatIBuild` (null → fallback, backward-compatible). (7) Extract shared experience/education/date formatters into pure helpers used by cv, linkedin, github (no output change). (8) Golden/snapshot tests for each generator's `output/*`.

### Out of Scope (Non-Goals)
- Visual redesign / "leveling up" LinkedIn/CV/portfolio to match the rich GitHub README (separate visual-approval change).
- Full local mirroring/caching of icon SVGs (only reachability here; note as future).
- Deploy automation (separate `profile-output-distribution` change).
- The monorepo restructure (separate parked change).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `profile-data`: validation becomes schema-authoritative via `jsonschema` (object/`oneOf`/required enforced); icon reachability warnings.
- `profile-outputs`: generators gain graceful error handling, consume `whatIBuildVariants` with fallback, share extracted formatters, and are golden-tested; CI runs the test suite; `generate_all.py` runs as script and module.

## Approach

Work bottom-up: fix the CI blind spot and runnability first, then make validation authoritative, then harden runtime UX, then refactor duplication under regression guards. Golden tests are established before the dedup refactor so byte-stable output is provable. `whatIBuildVariants` follows the existing use-if-present-else-fallback convention. Delivered as a single work unit at `size:exception` (user pre-approved).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.github/workflows/validate.yml` | Modified | Install deps + run `pytest` |
| `generators/generate_all.py` | Modified | Runs as script and module |
| `generators/validate.py` | Modified | `jsonschema`-based, authoritative schemas; keep CLI + cross-field warning |
| `pyproject.toml` | New/Modified | Add `jsonschema` dependency |
| `generators/generate_{cv,linkedin,github_readme,portfolio}.py` | Modified | Error handling + `whatIBuildVariants` + shared formatters |
| `generators/utils.py` or new `generators/render.py` | New/Modified | Shared experience/education/date formatters |
| icon reachability helper | New | Warn on unresolved slug/iconUrl |
| `tests/` (golden + unit) | New | Golden snapshots per generator output |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `jsonschema` dep unavailable in CI | Med | Pin in `pyproject`; CI installs before validate/pytest |
| Dedup refactor changes output bytes | Med | Golden tests land first; refactor must keep them green |
| Error handling masks real bugs | Low | Only catch known I/O/parse/missing-field cases; re-raise unexpected |
| Icon check network dependency in CI | Med | Non-fatal warnings only; opt-out flag / skip when offline |

## Rollback Plan

Each tier is independently revertible. Revert the CI workflow change to restore prior CI; revert `validate.py` to the hand-rolled version and drop the `jsonschema` dep; the dedup refactor reverts to per-generator formatters (golden tests confirm identical output either way). No data or schema files change, so no data migration or rollback is needed.

## Dependencies

- `jsonschema` (new Python dependency).
- A configured `pytest` runner (`pyproject`/CI); none exists today.

## Success Criteria

- [ ] CI installs deps and runs the full `pytest` suite (fails the build on test failure).
- [ ] `python generators/generate_all.py` and `python -m generators.generate_all` both succeed.
- [ ] `validate.py` enforces `schemas/*` via `jsonschema` (object/`oneOf`/required), keeps per-file PASS/FAIL + non-zero exit + `validate_portfolio_highlights` warning.
- [ ] Malformed/missing data yields a clear which-file/which-field message and non-zero exit, never a raw traceback.
- [ ] Unresolved icon slugs/URLs produce non-fatal build-time warnings.
- [ ] Generators consume `whatIBuildVariants[<platform>]` with fallback to `whatIBuild`.
- [ ] Shared formatters back cv/linkedin/github with byte-identical output (golden tests green).
