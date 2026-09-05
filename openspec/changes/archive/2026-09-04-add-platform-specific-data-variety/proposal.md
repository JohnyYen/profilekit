# Proposal: Add Platform-Specific Data Variety to profile-data

- Change: `add-platform-specific-data-variety`
- Status: proposed (specs authored)
- Created: 2026-09-04

## Problem Statement

The profile-data project currently presents identical data across all output
platforms (GitHub README, LinkedIn copy, CV, and the Next.js portfolio), with no
configurability for platform-specific variations:

- **Same data for all platforms**: The `headline` field in `about.json` is used
  verbatim for the GitHub README, LinkedIn copy, and CV headline — with no
  platform tailoring.
- **No configurability**: There is no way to specify different summaries or
  headlines for different platforms.
- **Data duplication in portfolio**: Portfolio entries repeat the same
  headline/description without platform-specific variations.

This creates a poor experience when the user wants to present different aspects
of their professional identity depending on context (GitHub vs LinkedIn vs CV vs
portfolio website).

## Proposed Solution (high level)

Add optional platform-specific fields to `about.json` that generators check and
use when present. When the fields are absent, generators fall back to existing
behavior unchanged. All changes are purely additive and backward-compatible:

- Introduce 5 new optional fields on `about.json` for platform tailoring.
- Extend `schemas/about.schema.json` with the new fields as optional properties
  (never added to `required`); existing data continues to validate.
- Update the three generators to use the platform-specific field when present and
  otherwise fall back to the current `headline`/`tagline` behavior.
- Document a lightweight integration pattern for the external Next.js portfolio
  to consume `portfolioHighlights`.

## Scope / Artifacts

| Path | Change Type |
|------|-------------|
| `data/about.json` | Add 5 new optional fields (githubReadmeSummary, linkedinHeadline, cvHeadline, portfolioHighlights, whatIBuildVariants) |
| `schemas/about.schema.json` | Add the 5 fields as optional properties; keep `additionalProperties: true`; do not modify `required` |
| `generators/generate_github_readme.py` | Check `githubReadmeSummary`; use if present, else fall back |
| `generators/generate_linkedin.py` | Check `linkedinHeadline`; use if present (respect 220-char limit), else fall back to truncation |
| `generators/generate_cv.py` | Check `cvHeadline`; use in the `design:` headline if present, else fall back |
| `app/data/` (documentation only) | Integration pattern for the Next.js portfolio consuming `portfolioHighlights` |

### New optional fields (data model)

1. `githubReadmeSummary` — `string | null`: concise summary for the GitHub README
   profile section; when present, overrides default headline/tagline rendering.
2. `linkedinHeadline` — `string | null`: LinkedIn-optimized headline (max 220
   chars); when present, used directly without truncation.
3. `cvHeadline` — `string | null`: headline for the CV/RenderCV `design:` section.
4. `portfolioHighlights` — `array of string | null`: subset of project names from
   `projects.json` (max 6) to feature in the portfolio.
5. `whatIBuildVariants` — `object | null`: platform keys (`github`, `linkedin`,
   `cv`, `portfolio`) mapped to platform-specific "what I build" descriptions.

## Non-Goals

- Do NOT restructure existing data — only add new optional fields.
- Do NOT change existing output format when the new fields are absent — fallbacks
  maintain backward compatibility.
- Do NOT remove the current LinkedIn headline truncation logic — it remains as
  the fallback.
- Do NOT migrate existing data — the user fills in optional fields when ready.
- Do NOT change the schema in a breaking way — all new fields are optional.

## Risks & Assumptions

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| User doesn't fill in optional fields | Low | Backward compatibility guaranteed — all generators fall back to existing behavior |
| `portfolioHighlights` references non-existent project names | Medium | Validation can check against `projects.json` names; script warns on mismatch |
| `whatIBuildVariants` keys don't match generator expectations | Low | Document expected keys (`github`, `linkedin`, `cv`, `portfolio`); each generator uses only its own key |
| LinkedIn headline exceeds 220 chars when user-provided | Medium | Generator truncates or warns; "use if present" places responsibility on the user input |
| Schema validation fails on wrong field types | Low | Schema defines correct types; new fields are optional so existing data passes |

**Assumptions:**

- The user will fill in optional fields when ready for platform-specific
  customization.
- The portfolio integration needs minimal changes — reading `about.json` and
  filtering `projects.json`.
- All changes are additive; no existing behavior is removed or altered when the
  fields are absent.

## Rollback Plan

Because the change is purely additive, rollback is low-risk: remove the new
property definitions from `schemas/about.schema.json`, revert the generator
diffs, and either drop the new keys from `about.json` or leave them as `null`
(generators ignore `null` and fall back). No data migration is required in either
direction.

## Next Recommended Step

Proceed to the `design` phase for the generator modifications and schema updates,
then `tasks` to slice the work into TDD-ordered implementation items.
