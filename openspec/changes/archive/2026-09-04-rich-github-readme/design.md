# Design: Rich Iconized GitHub Profile README

## Technical Approach

Add two pure helpers to `generators/utils.py` — `skill_name(entry)` and `skill_icon(entry)` — that normalize a skill detail that is EITHER a string OR `{name, icon?, iconUrl?}`. Every skill consumer routes through them, so string and object data render identically for existing outputs. Rewrite `generate_github_readme.py` into small pure render functions that emit GitHub-supported centered HTML. Widen `skills.schema.json` `details.items` to `oneOf[string, object]`. Seed `data/skills.json` with icon slugs. Bundle `assets/pixel-mario.gif`. Strict TDD (RED first).

## Architecture Decisions

### Skill normalization helpers in utils
**Choice**: `skill_name(e)` returns `e` if str else `e["name"]`; `skill_icon(e)` returns `None` for str, else `(e.get("icon"), e.get("iconUrl"))`.
**Alternatives**: per-generator inline ternaries. **Rationale**: one shared, tested source; zero-diff compat; DRY across 3 consumers.

### Schema uses oneOf, custom validator stays lenient
**Choice**: `details.items: { oneOf: [ {type:string}, {type:object, properties:{name,icon,iconUrl}, required:[name]} ] }`.
**Alternatives**: jsonschema lib; keep string-only. **Rationale**: The project's hand-rolled `generators/validate.py` has no `oneOf` branch — it skips items lacking a top-level `type`, so it stays non-breaking (string entries still validate, objects pass through untyped). Documenting this is load-bearing: strict object validation is NOT enforced by the current validator, so apply MUST rely on tests for object shape. No new dependency.

### Pure render functions, HTML strings
**Choice**: keep dict/list-in → string-out functions. **Rationale**: matches existing style; unit-testable without I/O.

### External icon services are view-time refs
**Choice**: emit `<img src="https://skillicons.dev/icons?i=<slug>">` / verbatim `iconUrl`. **Rationale**: GitHub resolves at view time; not a build dependency.

## Data Flow

    skills.json ──► skill_name/skill_icon ──► render_icon_rows ──► github-readme.md
         └──────────► render_linkedin_skills / cv skills (name-only, unchanged text)
    about.json ──► render_header/about/focus/learning/footer ──► github-readme.md
    profile repo gif ──(apply: gh api / raw)──► assets/pixel-mario.gif ──► <img src>

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `generators/utils.py` | Modify | Add `skill_name`, `skill_icon` |
| `generators/generate_github_readme.py` | Modify | Rewrite to centered HTML + icon rows |
| `generators/generate_linkedin.py` | Modify | `render_linkedin_skills` uses `skill_name` |
| `generators/generate_cv.py` | Modify | `format_skill_entry` + cv-md skills loop use `skill_name` |
| `data/skills.json` | Modify | String → `{name, icon?, iconUrl?}` objects |
| `schemas/skills.schema.json` | Modify | `details.items` → `oneOf[string,object]` |
| `assets/pixel-mario.gif` | New | Downloaded during apply |
| `tests/test_generate_github_readme.py` | Modify | Replace `render_about` tests with new HTML/icon tests |
| `tests/test_generate_linkedin.py` / `test_generate_cv.py` / `test_utils.py` | Modify | Object-vs-string compat regression |
| `tests/fixtures/skills.json` | Modify | Add one object entry for compat coverage |

`generate_portfolio.py`: NO CHANGE — it does not read skills.

## Interfaces / Contracts

```python
def skill_name(entry: str | dict) -> str          # entry if str else entry["name"]
def skill_icon(entry: str | dict) -> str | None   # skillicons slug | iconUrl | None
```

README render functions (pure): `render_header(about)`, `render_about_html(about)`, `render_focus(about)` (currentFocus bullets), `render_icon_rows(skills)`, `render_experience_text(experience)`, `render_learning(about)` (learningJourney), `render_footer(about)`.

`render_icon_rows`: per category emit `<div align="center">` of `<img src=... height="60">` joined by `<img width="15" />` spacers; `iconUrl` used verbatim else skillicons URL; entries with no icon omitted; categories with zero icons skipped entirely (Software Design, AI-Driven Development).

Asset path in generated readme: `<img src="assets/pixel-mario.gif" ...>` (relative; matches deploy target repo layout).

### Icon seed (skills.json)
`icon`: NestJS→nestjs, FastAPI→fastapi, .NET→dotnet, PostgreSQL→postgres, MongoDB→mongodb, Prisma ORM→prisma, Docker→docker, Git→git, GitHub Actions→githubactions, Vercel→vercel, GitHub→github, GitLab→gitlab, TypeScript→ts, Python→python, C#→cs, JavaScript→js.
`iconUrl` (skillicons gaps): Hono, Strapi → `https://devicons.railway.com/i/<name>.svg`.
No icon (plain string): Frappe, ERPNext (apply MUST verify a devicons svg; else omit), and all Software Design / AI-Driven Development entries.
Apply MUST verify each slug against the live skillicons catalog and fall back to `iconUrl` on any miss.

### about.json additions
Reuse existing fields (description, currentFocus, learningJourney). Add ONE optional field `githubQuote` (closing quote) only if the target README includes a quote; greeting name reuses `username`. Additive/backward-compatible; `about.schema.json` gets an optional string property.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `skill_name`/`skill_icon`: str, object w/ icon, object w/ iconUrl, no icon | table cases |
| Unit | `render_icon_rows`: object+icon → skillicons url; object+iconUrl → verbatim; string/no-icon omitted; empty category skipped | assert substrings |
| Unit | new README HTML sections (align, height/width, gif path) | substring asserts |
| Regression | linkedin/cv skills unchanged text with object AND string input | golden-string equality |
| Schema | string entries still validate; object entry accepted | `validate_file` |

Runner: `.venv/bin/python -m pytest -q`. RED tests written before implementation.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary in the generator/schema/data code. (The one-time asset download runs during apply, outside generator runtime.)

## Migration / Rollout

No data migration. `skills.json` stays valid as strings or objects; reverting generator/schema/data restores plain-markdown output.

## Open Questions

- [ ] Confirm target README includes a closing quote (drives `githubQuote` field).
- [ ] Verify Frappe/ERPNext have devicons SVGs; otherwise render as text.
