# Proposal: Rich Iconized GitHub Profile README

## Intent

`generators/generate_github_readme.py` emits plain markdown (`## About`, comma-joined skill lists). The user's real GitHub profile README (JohnyYen/JohnyYen) is centered HTML with a headline, a pixel-Mario gif, "What I focus on" bullets, and technology **icon rows grouped by category** (skillicons.dev + devicons SVG). Generated output is far from the profile people actually see. This change makes the generator reproduce that richly-styled look while keeping profile data canonical and every other generator green.

## Scope

### In Scope
- Rewrite `generate_github_readme.py` to emit centered HTML: `<h1>/<h2>` header, About prose + local Mario gif, "What I focus on" bullets, per-category icon rows, and text sections (Experience, Currently learning, closing invite + quote).
- Enrich `data/skills.json`: each skill entry becomes `{ "name": "NestJS", "icon": "nestjs" }` with optional `"iconUrl"` override (e.g. strapi, hono via `devicons.railway.com/i/<name>.svg`). Plain string entry = no icon (backward compatible).
- Update `schemas/skills.schema.json` so `details` items accept string OR object `{name, icon?, iconUrl?}`.
- Update ALL skill consumers (`generate_github_readme.py`, `generate_linkedin.py`, `generate_cv.py`) to read `entry["name"]` for objects and fall back to the raw string — no consumer breaks.
- Bundle `assets/pixel-mario.gif` in-repo (downloaded from the profile repo during apply); generator references it via `<img>`.
- Icon rendering: skillicons via `https://skillicons.dev/icons?i=<slug>`; overrides via `iconUrl`; conceptual categories (Software Design, AI-Driven Development) render as text/omitted from icon blocks.
- Tests: new github-readme render tests (HTML structure, icon rows, string/object compat) + regression coverage on linkedin/cv skill rendering.

### Out of Scope
- Deploy automation that copies output/assets to JohnyYen/JohnyYen.
- Changing the LinkedIn / CV / portfolio VISUAL style — they receive only the object/string compat fix.
- Icon rendering for conceptual skill categories.

## Capabilities

### New Capabilities
- `github-readme-generation`: rules for the iconized, centered HTML GitHub profile README output.

### Modified Capabilities
- `skills-data-model`: skill entries may be strings or `{name, icon?, iconUrl?}` objects; all consumers read name-or-string. (If no such spec exists yet, sdd-spec creates it.)

## Approach

Introduce a small helper (`skill_name(entry)` / `skill_icon(entry)`) shared by consumers to normalize string-vs-object entries. The README generator iterates categories, rendering an icon `<div align="center">` when entries carry `icon`/`iconUrl`, otherwise plain text. Header, About+gif, focus bullets, and closing sections are HTML templates fed by existing `about.json`/`experience.json` fields. Schema widened to `oneOf`. Strict TDD: write failing render/compat tests first.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `generators/generate_github_readme.py` | Modified | Full rewrite to centered HTML + icon rows |
| `data/skills.json` | Modified | String entries → `{name, icon, iconUrl?}` objects |
| `schemas/skills.schema.json` | Modified | `details` items accept string or object |
| `generators/generate_linkedin.py` | Modified | Compat fix in `render_linkedin_skills` |
| `generators/generate_cv.py` | Modified | Compat fix in `format_skill_entry` + `render_cv_markdown` |
| `assets/pixel-mario.gif` | New | Bundled local asset |
| `tests/test_generate_github_readme.py` (+ linkedin/cv/schema tests) | Modified/New | Render + compat coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Wrong skillicons slug mapping | Med | Curate slugs against skillicons catalog; `iconUrl` override for gaps (strapi, hono) |
| External icon service (skillicons/devicons) downtime | Low | Icons are `<img>` refs resolved by GitHub at view time; not a build dependency |
| HTML-in-markdown rendering differences on GitHub | Med | Use GitHub-supported subset (`align`, `<img height/width>`); verify against real profile structure |
| Compat fix regresses other generators | Med | TDD regression tests on linkedin/cv skill rendering before edit |
| Schema change rejects existing string entries | Low | `oneOf[string, object]`; keep string path valid |

## Rollback Plan

Revert the change commit(s). Since `skills.json` remains valid as either strings or objects and consumers accept both, reverting only the generator/schema/data files restores prior plain-markdown output with no data migration needed.

## Dependencies

- `assets/pixel-mario.gif` must be downloaded from the profile repo during apply.
- skillicons.dev / devicons.railway.com slug references (view-time only).

## Success Criteria

- [ ] `output/github-readme.md` renders centered HTML header, Mario gif, focus bullets, per-category icon rows, and closing sections matching the target style.
- [ ] `skills.json` uses `{name, icon}` objects with `iconUrl` overrides where needed; schema validates it.
- [ ] `generate_linkedin.py` and `generate_cv.py` produce unchanged skill text output from the new object model.
- [ ] Full test suite passes (existing + new).
