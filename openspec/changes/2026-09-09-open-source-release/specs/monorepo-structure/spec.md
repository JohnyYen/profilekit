# Delta for monorepo-structure

## ADDED Requirements

### Requirement: No tracked noise or third-party scraped content

The repository MUST NOT track development-tool noise (session logs, page
dumps, screenshots) or scripts that scrape a third party's content.
Specifically, `apps/portfolio/.playwright-cli/`, `apps/portfolio/.agents/`,
`apps/portfolio/.claude/skills/playwright-cli/`, `cv/.agents/`, tracked
screenshot PNGs, and `apps/portfolio/scripts/analyze-portfolio.js` MUST be
removed from tracked files. `.codegraph/` MUST be listed in `.gitignore`.

#### Scenario: Noise paths absent from the tracked tree

- GIVEN the repository after this change is applied
- WHEN `git ls-files` is run
- THEN none of the listed noise paths SHALL appear
- AND `apps/portfolio/scripts/analyze-portfolio.js` SHALL NOT exist

#### Scenario: .codegraph/ is ignored

- GIVEN `.codegraph/` exists on disk from local tool use
- WHEN `git status` is run
- THEN `.codegraph/` SHALL NOT appear as untracked

### Requirement: No absolute developer paths in tracked files

No tracked file MUST contain an absolute filesystem path rooted at a
specific developer's home directory (e.g. `/home/johny/...`).

#### Scenario: Grep gate for absolute paths

- GIVEN the full set of tracked files
- WHEN they are scanned for a pattern matching an absolute home-directory
  path
- THEN no match SHALL be found

### Requirement: Vendored cv/ subtree deploy workflow is inert or resolved

The vendored `cv/` git subtree's own dormant workflow
(`cv/.github/workflows/render-cv.yml`, which declares `contents: write` and
a release action) MUST NOT be capable of running from this repository,
whether by removal, disabling, or exclusion from the subtree sync.

#### Scenario: cv/ workflow does not run in this repository's CI

- GIVEN `cv/` is present in the repository
- WHEN GitHub Actions evaluates workflows for this repository
- THEN only workflows under the repository's own root `.github/workflows/`
  SHALL run
- AND `cv/.github/workflows/render-cv.yml` SHALL NOT execute, or SHALL have
  been removed or disabled

### Requirement: apps/portfolio documented as a non-distributed reference consumer

`apps/portfolio/README.md` MUST describe the application as the
maintainer's own reference implementation of a data consumer, explicitly
not distributed as part of the installable package. It MUST NOT be
unmodified create-next-app boilerplate.

#### Scenario: Portfolio README describes its role

- GIVEN `apps/portfolio/README.md`
- WHEN it is read
- THEN it SHALL state that the app is a reference consumer of the data
  contract and is not shipped with the package
- AND it SHALL NOT contain unmodified create-next-app boilerplate text

#### Scenario: Portfolio still builds after hygiene pass

- GIVEN the hygiene changes and the README replacement have been applied
- WHEN the portfolio app is built as described in this spec's existing
  build requirement
- THEN the build SHALL succeed exactly as it did before this change
