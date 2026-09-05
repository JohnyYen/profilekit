# Profile Data — Single Source of Truth

Canonical structured data for Johny A. Pedraza Romero's public profiles.

## Consumers

| Consumer | Repo | How it consumes |
|---|---|---|
| CV (RenderCV) | `JohnyYen/my-cv` | `generators/generate_cv.py` → RenderCV YAML → GitHub Action → PDF release |
| Portfolio | `JohnyYen/my-portfolio-terminal` | Fetch `data/*.json` from `raw.githubusercontent.com` at build (ISR) |
| GitHub Profile | `JohnyYen/JohnyYen` | Workflow runs `generators/generate_github_readme.py` → commits README |
| LinkedIn | Manual | `generators/generate_linkedin.py` → copy-paste text |

## Data Files

- `data/about.json` — name, headline, tagline, bio, location, email, phone, languages
- `data/social.json` — github, linkedin, website, cvUrl
- `data/experience.json` — work history
- `data/education.json` — academic background
- `data/projects.json` — canonical project list
- `data/skills.json` — categorized skills
- `data/publications.json` — publications (placeholder)
- `data/interests.json` — personal interests

## Schema

Each file has a corresponding JSON Schema in `schemas/`. Run `profile validate` to validate.

## CLI

A single entry point wraps all generators. Run it as a module, or as the
`profile` console script after `pip install -e .`:

```sh
python -m generators.cli <command>     # no install needed
profile <command>                      # after `pip install -e .`
```

| Command | Does |
|---|---|
| `generate [target]` | Generate one target or `all` (default). Targets: `github-readme`, `linkedin`, `portfolio`, `cv` |
| `validate` | Validate `data/*.json` against `schemas/` |
| `check` | Validate, regenerate, and fail if committed `output/` is stale (CI-parity gate) |
| `list` | List available generation targets |

The legacy invocations (`python -m generators.generate_all`,
`python -m generators.validate`, and individual `generate_*` modules) still work.

## Editing

1. Edit the relevant `data/*.json` file(s)
2. Run `profile validate` to check
3. Run `profile generate [target]` to produce artifacts
4. Commit and push — downstream consumers pick up changes on their next build
