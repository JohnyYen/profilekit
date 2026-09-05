# Design: Platform-Specific Data Variety

## Technical Approach

Additive, use-if-present-else-fallback tailoring driven entirely by
`data/about.json`. Each generator reads its own optional field with
`about.get(field) or <existing-fallback>`, so `None`, missing, and empty-string
all collapse to legacy behavior. Schema and data already carry the five fields as
`null` placeholders; work is per-generator wiring plus a `portfolioHighlights`
validation and a first-time pytest scaffold (Strict TDD requires it).

Grounded in spec `specs/profile-data/spec.md` and `proposal.md`.

## Current-State Findings (read, not assumed)

- `schemas/about.schema.json` already declares all 5 fields as optional with
  correct types; `required` stays `["username","tagline","description"]`;
  `additionalProperties: true`. No schema change needed beyond confirmation tests.
- `data/about.json` already has the 5 keys set to `null`.
- `generate_github_readme.py:39` already implements the fallback via a walrus
  (`about.get('githubReadmeSummary') or about.get('headline', about.get('tagline',''))`).
  Keep; only add tests. Output line: `**{username}** — {display}`.
- `generate_linkedin.py` and `generate_cv.py` still use the legacy headline path —
  these need the wiring.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Field access | `about.get(f) or fallback` | explicit `is not None` checks | `or` treats null/missing/"" uniformly as "not set" per spec null-handling scenarios; matches existing README line 39 |
| Fallback location | inline at each use-site | shared helper module | Generators are standalone scripts with no shared lib; a helper adds coupling for a one-liner. Follow existing per-file pattern |
| LinkedIn 220-char | truncate (reuse `truncate_headline`) + stderr warn when input >220 | trust blindly / hard fail | Spec: "MUST NOT emit >220"; reusing existing word-safe truncator guarantees the invariant and keeps one code path. Warn preserves user signal without breaking generation |
| CV headline placement | RenderCV `design:` needs no `headline` key; the CV headline is `cv.headline`. Apply `cvHeadline` to the `cv.headline` line (`generate_cv.py:111`) | add a `headline:` under `design:` | RenderCV v2 schema has no `design.headline`; emitting it produces an invalid CV. Spec wording ("design: section") is imprecise vs the real schema. **Open question below** — flag, follow real schema |
| portfolioHighlights validation | extend `generators/validate.py` with a cross-file check: warn (non-fatal) on unmatched names and on >6 entries | fail build / new script | Spec says SHOULD warn, not fail; validate.py is the existing validation home |

## Data Model (field → output mapping)

| Field | Type | Consumer | Output |
|-------|------|----------|--------|
| `githubReadmeSummary` | string\|null | README | `**{username}** — {summary}` |
| `linkedinHeadline` | string\|null | LinkedIn | `## Headline` body, ≤220 chars |
| `cvHeadline` | string\|null | CV | `cv.headline` YAML line (escaped) |
| `portfolioHighlights` | array\<string\>\|null (≤6) | portfolio (external) + validate.py | doc + warning check |
| `whatIBuildVariants` | object\|null keyed `github`/`linkedin`/`cv`/`portfolio` | future per-platform "What I Build" | documented; each generator reads only its own key |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `generators/generate_linkedin.py` | Modify | `main`: `raw = about.get('linkedinHeadline') or about.get('headline', about.get('tagline',''))`; emit `truncate_headline(raw)`; warn to stderr if `len(raw) > 220` |
| `generators/generate_cv.py` | Modify | line 111: `about.get('cvHeadline') or about.get('headline', about.get('tagline',''))` before `escape_yaml_string` |
| `generators/validate.py` | Modify | add `validate_portfolio_highlights()` cross-checking against `projects.json` names; warn on unmatched / >6; non-fatal |
| `generators/generate_github_readme.py` | Confirm | already correct; covered by tests only |
| `schemas/about.schema.json` | Confirm | already correct; covered by tests only |
| `tests/` + `pytest.ini` (or `pyproject.toml`) | Create | new test scaffold (see below) |
| `app/data/` docs (README note) | Create/Modify | portfolio integration pattern for `portfolioHighlights` (doc only) |

## Testing Strategy (Strict TDD — scaffold required)

The repo has **no test runner today**. Add **pytest** (dev dependency) with
tests under `tests/` at repo root; `test_command: pytest -q`. Tests import the
generator modules and call their pure functions / `main` with monkeypatched
`load_json` (or a temp `data/` fixture dir) and assert on returned strings.

RED-GREEN-REFACTOR order per requirement:

| Layer | Test | Approach |
|-------|------|----------|
| Unit | README summary present / absent-fallback / null-fallback | call `render_about(about_dict)`, assert display line |
| Unit | LinkedIn present ≤220 / >220 truncated / absent-fallback | assert emitted headline & `len ≤ 220`; capture stderr warn |
| Unit | CV `cvHeadline` present / absent-fallback | assert `cv.headline` line, YAML-escaped |
| Unit | Schema: legacy validates / typed fields validate / wrong type fails | run `validate_file('about.json')` on fixtures |
| Integration | `portfolioHighlights` all-valid / unmatched warns / >6 warns / null | run `validate_portfolio_highlights` against `projects.json` fixture |

Each generator currently writes files in `main`; add tests against the pure
render functions where they exist, and for LinkedIn/CV factor the headline
computation so it is unit-testable without disk writes (minimal extraction only
if needed for RED test).

## Data Flow

    about.json (optional field) ─┐
                                 ├─→ generator.get(field) or fallback ─→ output artifact
    headline/tagline (fallback) ─┘

    portfolioHighlights ─→ validate.py ──cross-check──→ projects.json names ─→ warn|ok

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Generators read local JSON and
write local text/YAML.

## Migration / Rollout

No migration. Fields already present as `null`; behavior unchanged until values
are filled. Rollback = revert generator diffs (fields stay null → legacy path).

## Open Questions

- [ ] CV headline placement: spec says "design: section" but RenderCV v2 has no
  `design.headline`; design applies `cvHeadline` to `cv.headline`. Confirm this
  interpretation before apply (tasks should encode `cv.headline`).
- [ ] `whatIBuildVariants` has no generator wiring in this change (data/doc only)
  — confirm it stays documentation-only for now, matching proposal scope.
