# Profile Data — Single Source of Truth (Monorepo)

Canonical structured data for Johny A. Pedraza Romero's public profiles, plus the
Python pipeline that turns it into every published surface. Edit the data once in
`data/*.json`; the generators produce the GitHub profile README, LinkedIn copy,
CV, and feed the in-repo portfolio app.

## Repository layout

| Path | What it is |
|---|---|
| `data/` | **Canonical profile data** (JSON) — the single source of truth |
| `schemas/` | JSON Schemas validating each `data/*.json` |
| `generators/` | Python generation pipeline (data → artifacts) |
| `output/` | Generated artifacts, committed: `github-readme.md`, `linkedin.md`, `portfolio.md`, `cv.md`, `cv.yml` |
| `apps/portfolio/` | In-repo Next.js "terminal" portfolio (consumes canonical data) |
| `cv/` | In-repo RenderCV project |
| `tests/` | pytest suite (golden snapshots + unit tests) |
| `openspec/` | Spec-Driven Development artifacts (specs + archived changes) |
| `.github/workflows/` | CI (validation, tests, quality gates) |

## Data flow

```
data/*.json ──▶ generators/ ──▶ output/*.{md,yml}              ──▶ GitHub profile / LinkedIn / CV
                          └────▶ apps/portfolio/app/data/*.json ──▶ terminal portfolio app
```

`data/` is the only hand-authored source. Everything under `output/` and
`apps/portfolio/app/data/` is **generated** and committed as a reviewable artifact.

## Data files

- `data/about.json` — name, headline, tagline, bio, location, contact, languages, focus, and per-platform variants
- `data/social.json` — github, linkedin, email, cvUrl
- `data/experience.json` — work history
- `data/education.json` — academic background
- `data/projects.json` — canonical project list
- `data/skills.json` — categorized skills (with icon slugs)
- `data/publications.json` — publications (placeholder)
- `data/interests.json` — personal interests (placeholder)

## CLI

A single entry point wraps all generators. Run it as a module, or as the
`profile` console script after `pip install -e .` (or `uv sync --extra dev`):

```sh
python -m generators.cli <command>     # no install needed
profile <command>                      # after install
```

| Command | Does |
|---|---|
| `generate [target]` | Generate one target or `all` (default). Targets: `github-readme`, `linkedin`, `portfolio`, `cv` |
| `validate` | Validate `data/*.json` against `schemas/` |
| `check` | Validate, regenerate, and fail if committed `output/` is stale (CI-parity gate) |
| `list` | List available generation targets |

`generate all` also syncs canonical data into `apps/portfolio/app/data/` via
`generate_portfolio_data.py`. Legacy invocations (`python -m generators.generate_all`,
`python -m generators.validate`, individual `generate_*` modules) still work.

## Editing

1. Edit the relevant `data/*.json` file(s).
2. `profile validate` — check against schemas.
3. `profile generate` — regenerate `output/` and the portfolio's app data.
4. Commit `data/` **and** the regenerated artifacts, then push.

The `output/` freshness gate in CI fails the build if committed artifacts don't
match a fresh generation, so always commit the regenerated output.

## Development

```sh
uv sync --extra dev          # install runtime + dev deps into .venv
uv run pytest -q             # tests + coverage (fails under 80%)
uv run ruff check . && uv run ruff format --check .
uv run mypy generators/
uv run pre-commit install    # optional: run the gates on every commit
```

CI (`.github/workflows/validate.yml`) runs ruff, mypy, pytest+coverage, data
validation, and the `output/` freshness gate. Icon/link reachability checks are
skippable via `SKIP_ICON_CHECK=1` / `SKIP_LINK_CHECK=1`.

## Published destinations

| Surface | Destination | How |
|---|---|---|
| GitHub profile | `JohnyYen/JohnyYen` | Deploy `output/github-readme.md` (icons via skillicons.dev) |
| Portfolio | `apps/portfolio/` (in-repo) | Reads `apps/portfolio/app/data/` synced from `data/`; live GitHub API is primary for projects |
| CV | `cv/` + `JohnyYen/my-cv` | `output/cv.yml` (RenderCV) → PDF release; `output/cv.md` is the readable version |
| LinkedIn | Manual | Paste `output/linkedin.md` |

## Planning workflow

Non-trivial changes are planned with Spec-Driven Development under `openspec/`
(proposal → spec → design → tasks → apply → verify → archive). Completed changes
are archived in `openspec/changes/archive/`.
