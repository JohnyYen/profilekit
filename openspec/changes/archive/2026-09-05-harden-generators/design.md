# Design: Harden the Profile Generator Pipeline

## Technical Approach

Work bottom-up in four tiers (CI/runnability → authoritative validation → runtime robustness → quality/dedup), each independently revertible. Generators stay pure transforms with `use-if-present-else-fallback` semantics. Golden snapshots are locked immediately before the dedup refactor so byte-stability is provable. Test runner: `.venv/bin/python -m pytest -q` (76 tests today).

**Grounded facts that shape this design:**
- `whatIBuild` AND `whatIBuildVariants` are dead data — no generator reads them (`grep` confirms zero hits in `generators/`). Wiring is therefore NEW output, not a byte-stable rewrite. Byte-stability applies only to the dedup refactor (item 7), not to variant wiring (item 6).
- `tests/test_schema.py::test_skills_object_missing_name_invalid` asserts the current validator *passes* a missing-`name` object (documented limitation). jsonschema will *reject* it — this test MUST be flipped as part of item 3.
- All six schemas are draft-07 and jsonschema-valid; `skills.schema.json` uses `oneOf[string, object(required name)]` which jsonschema enforces natively.

## Architecture Decisions

| # | Decision | Choice | Rejected | Rationale |
|---|----------|--------|----------|-----------|
| D1 | CI structure | Single `validate` job: setup-python → `pip install -e ".[dev]"` → `pytest -q` → `validate.py` | Split test/validate jobs | One repo, fast suite; split adds matrix overhead with no benefit. Sequential steps give clear failure attribution. |
| D2 | `generate_all` runnability | Add `sys.path` bootstrap guard under `if __name__ == "__main__"` inserting `ROOT_DIR` on `sys.path[0]` before importing generators | Convert to `importlib`; drop package imports | Minimal diff; keeps `-m generators.generate_all` working (package import path unchanged) AND fixes bare `python generators/generate_all.py` (currently fails: `generators` not importable). |
| D3 | Validator engine | Rewrite `validate.py` internals on `jsonschema.Draft7Validator`; keep CLI, PASS/FAIL table, exit codes, cross-field warning | Keep hand-rolled; jsonschema CLI | Schemas become authoritative (object/`oneOf`/required/format). Preserving the public surface (`validate_file`, `validate_portfolio_highlights`, `main`) keeps existing tests green except the one documented boundary test. |
| D4 | Error handling | Typed `DataError(Exception)` raised by a strict loader in `utils.py`; each generator's `main` wrapped by a `run(main)` helper that catches `DataError` → stderr message + `exit(1)`, re-raises everything else | Broad `try/except Exception`; per-generator try blocks | Only known I/O/parse/missing-field cases are caught; unexpected bugs still surface tracebacks. Central helper avoids duplication. |
| D5 | Icon reachability | Helper `check_icons(skills, offline)` in new `generators/icons.py`, invoked from `validate.py` main; HEAD (fallback GET) each resolved skillicons URL / `iconUrl`; non-200 → stderr WARNING; skipped when `SKIP_ICON_CHECK=1` or `--offline` | Fatal check; per-generator checks | Network flakiness must never fail CI. Central, opt-out, warning-only. CI sets `SKIP_ICON_CHECK=1`. |
| D6 | Variant wiring | Pure helper `what_i_build(about, platform) -> list[str]` in `utils.py`: returns `[variants[platform]]` if truthy, else `whatIBuild` list, else `[]`. Each generator renders a small "What I build" section only when non-empty | Inline per-generator lookups | Single fallback rule; NEW output section (variants are dead data today), goldens authored fresh. |
| D7 | Shared formatters | New `generators/render.py` with pure helpers: `format_date_range(start, end, default_end)`, `format_experience_entry_*`, `format_education_entry_*` extracted from cv/linkedin/github | Put in `utils.py` | `utils.py` is I/O-focused; `render.py` isolates presentation. Extraction must be behavior-preserving — locked by goldens (D8). |
| D8 | Golden tests | Store expected `output/*` under `tests/golden/`; a `test_golden.py` runs each generator into a tmp `OUTPUT_DIR` and asserts byte-equality; regen via `REGEN_GOLDEN=1 pytest`. Land goldens AFTER items 1-6, BEFORE item 7 | Inline expected strings; approve-tests lib | File goldens are readable diffs and lock the dedup refactor. Ordering makes refactor provably safe. |

## Data Flow

```
data/*.json ──> utils.load_json (strict, DataError) ──> generators.main
                                                            │
                          what_i_build(about, platform) ────┤ (new section)
                          render.format_* (shared) ─────────┤
                                                            ▼
                                                    write_output ──> output/*
schemas/*.schema.json ──> jsonschema.Draft7Validator ──> validate.py (PASS/FAIL + exit)
                                                            └─> icons.check_icons (WARN, skippable)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/validate.yml` | Modify | Add `pip install -e ".[dev]"`, `pytest -q` step (with `SKIP_ICON_CHECK=1`), then `validate.py`; pin python to a 3.11+ available runtime |
| `pyproject.toml` | Modify | Add `jsonschema` to `[project] dependencies`; add `requests` (or use stdlib `urllib`) for icon check |
| `generators/generate_all.py` | Modify | `sys.path` bootstrap under `__main__` |
| `generators/validate.py` | Modify | jsonschema engine; map `data/X.json` → `schemas/X.schema.json`; keep table/exit/warning; call `check_icons` |
| `generators/utils.py` | Modify | Add `DataError`, strict `load_json_strict`, `run(main)` wrapper, `what_i_build` |
| `generators/render.py` | Create | Shared experience/education/date formatters |
| `generators/icons.py` | Create | `check_icons` reachability helper (warning-only, skippable) |
| `generators/generate_{github_readme,linkedin,cv,portfolio}.py` | Modify | Adopt `run()`/DataError, `what_i_build` section, shared `render.*` |
| `tests/golden/*` | Create | Byte-exact expected outputs |
| `tests/test_golden.py` | Create | Golden comparison + `REGEN_GOLDEN` regen path |
| `tests/test_schema.py` | Modify | Flip `test_skills_object_missing_name_invalid` to expect FAIL under jsonschema |
| `tests/test_icons.py`, `tests/test_render.py`, `tests/test_what_i_build.py` | Create | Unit coverage for new helpers (mock network for icons) |

## Interfaces / Contracts

```python
class DataError(Exception):
    """Raised for known data faults (missing file/field, malformed JSON) with file+field context."""

def what_i_build(about: dict, platform: str) -> list[str]:  # variants[platform] | whatIBuild | []
def run(main_fn) -> None:  # catch DataError -> stderr+exit(1); re-raise unexpected
def check_icons(skills: dict, *, offline: bool = False) -> list[str]:  # returns warnings, never raises
```

Data-file→schema map (validate.py): each of `about, social, experience, education, projects, skills` → `schemas/<name>.schema.json`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `what_i_build` fallback matrix; `render.*` formatters; `DataError`/`run` paths; `check_icons` (mocked non-200) | pytest, monkeypatched network/data dirs |
| Integration | `validate.py` PASS on real data, FAIL on injected bad data, `oneOf`/required/format enforced; missing-name skills now rejected | tmp data dirs + monkeypatched DATA_DIR/SCHEMAS_DIR |
| E2E/Subprocess | `python generators/generate_all.py` AND `python -m generators.generate_all` exit 0 | `subprocess.run` asserting `returncode == 0` |
| Golden | Each generator output byte-equals `tests/golden/*` | run into tmp OUTPUT_DIR, compare; regen flag |

## Threat Matrix

Subprocess/process-integration boundaries exist (icon HTTP reachability; `generate_all` subprocess test; CI shell). Applicable rows:

| Row | Status | Safe behavior | RED test |
|-----|--------|---------------|----------|
| Outbound network (icon check) | Applicable | Never fatal; skippable via `SKIP_ICON_CHECK`/`--offline`; timeout-bounded | `check_icons` with mocked timeout/non-200 returns warnings, raises nothing |
| Subprocess invocation (`generate_all`) | Applicable | No shell string interpolation; use `subprocess.run([...])` arg list | subprocess test asserts exit 0, no shell=True |
| CI command execution | Applicable | Pinned deps, `SKIP_ICON_CHECK=1` in CI to avoid flakiness | CI runs `pytest` then `validate.py` |
| Executable-file classification / VCS-PR automation / routing | N/A | No such boundary in this change | — |

## Migration / Rollout

No data or schema files change; no data migration. Each tier reverts independently (see proposal rollback). The one behavioral test flip (`test_skills_object_missing_name_invalid`) ships in the same commit as the jsonschema migration.

## Open Questions

- [ ] CI python: workflow pins `3.14`; confirm the chosen runtime has a wheel for `jsonschema`/`requests` (prefer stdlib `urllib` for icon check to avoid the extra dep — recommended).
- [ ] Placement of the new "What I build" section within each output (top vs after focus) — pick during tasks; goldens lock it once chosen.
