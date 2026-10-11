# Proposal: Open Source Release

## Intent

Today this repo is **one person's profile data that happens to ship generators**. For a third
party it is unusable: no LICENSE (legally all-rights-reserved), no publishable `pyproject.toml`
metadata, and every module resolves its directories from `__file__` (`generators/utils.py:8-10`,
`cli.py:18-29`, `validate.py:11-14`), so an installed package would read data from inside
site-packages instead of the user's project.

This change **inverts the relationship**: become a *generation tool that ships an example
profile*. The owner's data becomes a fixture; the engine becomes the product, distributed as an
installable Python package on PyPI.

The reframe requires a three-layer architecture that does not exist yet:

```
AUTHORING          GENERATION                DISTRIBUTION
data/*.json  ──▶   generators/   ──▶ output/ ──┬──▶ publishers/ ──▶ destinations (push)
                   pure, no network  versioned └──▶ consumers (pull)
```

**Generator** = data → artifact: pure, no network, no credentials, golden-testable.
**Publisher** = artifact → destination: network, credentials, external side effects. Does not exist.

The boundary is already violated, with a shipped bug to prove it:

- `generate_portfolio_data.py:20` hardcodes a non-overridable write path outside `output/`. It is a
  publisher wearing a generator's name.
- The target registry is duplicated: `cli.py:33-38` (4 entries, comment claims "single source of
  truth") vs `generate_all.py:20-24,33-37` (5 entries). **They have diverged.** `profile generate
  all` never runs `portfolio_data`, contradicting `README.md:68-70`, and because CI's freshness gate
  runs the CLI path (`.github/workflows/validate.yml:64`), app-data drift is **ungated today**.

## Scope

| # | Deliverable | Impact |
|---|---|---|
| R0 | Repo hygiene: untrack 62 noise files (`.playwright-cli/`, screenshots, `.agents/`), delete the third-party scraper `apps/portfolio/scripts/analyze-portfolio.js`, resolve the vendored `cv/` subtree and its dormant `contents: write` workflow, refresh the stale `openspec/config.yaml` `context:` block, gitignore `.codegraph/` | Removed/Modified |
| R1 | Legal + package identity: LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG; full `pyproject.toml` metadata; rename the top-level `generators` package (PyPI namespace collision); `MANIFEST.in`, `py.typed`, packaged schemas | New/Modified |
| R2 | Separate generation from publication: generators write **only** inside the configured output dir, enforced by a test; `generate_portfolio_data` reclassified as a publisher with a configurable destination | Modified |
| R3 | Public data contract: `schemaVersion` on generated artifacts, documented shapes, publicly referenceable schemas — **this is the third-party product** | New |
| R4 | Publication layer: `profile publish [dest\|all]`, config-declared destinations, per-destination capability (`push`\|`manual`) and credentials, `--dry-run` default, content-hash idempotency, failure isolation, working core with zero credentials | New |
| R5 | CI automation: `publish.yml` on push to main gated on `output/` changing; optional per-destination secrets (absent = skip with log, not failure); `workflow_dispatch` dry-run; kept separate from `validate.yml` | New |
| R6 | Decouple paths: CWD-based project discovery, `profile.toml`, externalize baked-in opinions (`generate_github_readme.py:38,78,180`; `generate_cv.py:180,216-238`), `profile init`, `profile check` degrades without git | Modified |
| R7 | Single registry: entry-point discovery for generators **and** publishers; removes the duplication and fixes the `portfolio_data` bug | Modified |
| R8 | Test neutrality: fictional persona, zero real PII, goldens against a test dataset, tests run in `tmp_path`, delete the `JohnyYen` invariant (`tests/test_monorepo_layout.py:59`) | Modified |
| R9 | `apps/portfolio/` documented as a non-distributed reference consumer; replace its create-next-app boilerplate README | Modified |
| R10 | Docs, DX, release: README reframed as a tool, `docs/` with the data contract plus generator/publisher authoring guides, pre-commit without a hard `uv` dependency, PyPI publish on tag | New/Modified |

Sequencing: **R0 → R1 → R2 → R6 → R8 → R7 → R3 → R4 → R5 → R9 → R10.** R2 is a pure refactor with
no outward contract change, so it lands early. R4/R5 touch credentials and the real world, so they
land last — no debugging tokens while paths are still moving.

### Non-Goals

- **Parametrizing `apps/portfolio/`'s own identity.** It stays the owner's branded portfolio, kept
  as a *reference consumer* of the data contract. It is not distributed with the package. Third
  parties bring their own frontend.
- **A LinkedIn auto-publisher.** LinkedIn does not grant write access to profile fields without
  partner-level approval. LinkedIn is modeled as a `manual` destination that emits its artifact and
  reports a pending action. The layer MUST NOT report success for a publish it did not perform.
- **Resolving `openspec/changes/2026-09-05-add-generator-cli/`** (applied but never archived) — a
  pre-existing loose end, untouched here.
- Removing PII from `data/` is in scope only as part of test neutrality (R8) and the hygiene pass;
  redesigning the personal data model is not.

## Capabilities

### New Capabilities
- `package-distribution`: installable package identity, legal files, PyPI metadata and tag release.
- `project-configuration`: CWD project discovery, `profile.toml`, `profile init`, externalized
  generator opinions, git-less `profile check`.
- `component-registry`: entry-point discovery for generators and publishers.
- `output-data-contract`: versioned, documented, publicly referenceable artifact shapes.
- `publication`: `profile publish`, destination capability model, dry-run default, idempotency, CI.

### Modified Capabilities
- `profile-outputs`: generators write only inside the *configured* output dir, not a `__file__`-derived one.
- `portfolio-data-sync`: reclassified from generator to publisher with a configurable destination.
- `generator-tooling`: test neutrality, hygiene, pre-commit without `uv`, docs surface.
- `monorepo-structure`: `apps/portfolio/` as non-distributed reference consumer; noise untracked; `cv/` resolved.

## Approach

Refactor first, distribute last. Establish the generator/publisher boundary and configurable paths
over existing, well-tested code (152 tests, 80% coverage gate) before any outward-facing behavior
exists. Neutralize tests against a fictional dataset so the owner's data can change freely. Replace
both hardcoded registries with one entry-point registry, which fixes the divergence bug structurally
rather than by editing the second list. Only then add the publication layer, which is opt-in,
dry-run by default, and functional with zero credentials.

## Open Design Question (for `design.md`)

**Does the publication layer (R4) ship inside the distributed package, or stay as repo-local
`.github/` workflows?** The owner has not decided; `design.md` must resolve it.

**Recommendation:** ship the publication *core* in the package (destination protocol, capability
model, dry-run, content-hash idempotency, failure isolation), with concrete credentialed adapters as
opt-in entry-point plugins, and the CI workflow as a documented template rather than package logic.

**Tradeoff, stated plainly:** in-package publication expands the package's attack surface and makes
credential handling a maintenance and security obligation of a public artifact. Repo-local-only
keeps the package pure and auditable, but denies third parties the automation that makes the tool
worth adopting, forcing each one to reimplement it. The recommendation splits the difference; the
cost is one more extension point to document and support.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Path decoupling (R6) breaks generation for the owner's own repo | Med | R6 lands before publication work; existing golden + freshness gates stay green throughout |
| Renaming the `generators` package breaks imports/tests broadly | Med | Mechanical rename in one commit; full suite is the gate; no behavior change |
| Publication layer leaks credentials or writes to a real destination during tests/CI | Med | `--dry-run` default, opt-in publishers, absent secrets skip rather than fail, `publish.yml` separate from `validate.yml` |
| Claiming a publish that did not happen (LinkedIn class of destination) | Med | `manual` capability is a first-class state; verify write capability before claiming `push` |
| Untracking `cv/` history or subtree files loses work | Low | `git subtree split` remains available; nothing is deleted from remotes |
| PII remains in tracked data/goldens after the neutrality pass | Med | R8 makes the test dataset fictional; grep gate for the owner's name/email/phone in test fixtures |

## Rollback Plan

**Reversible (revert the commit):** R0, R2, R6, R7, R8, R9, R10 and the docs half of R1 are internal
refactors and repo hygiene. Nothing outside the repo observes them; reverting restores prior
behavior, and CI's existing freshness + golden gates detect regressions before merge.

**Crosses an irreversible line — treat as one-way doors:**

- **PyPI publication (R1/R10).** Publishing claims a global package name and a version number that
  cannot be reused or truly deleted. Mitigation: settle the package rename first, dry-run to
  TestPyPI, and publish only on an explicit tag.
- **The publication layer (R4/R5) performs outward-facing writes.** A push to a real destination
  cannot be reverted by reverting a commit. Mitigation: `--dry-run` default, per-destination opt-in,
  content-hash idempotency, and failure isolation so one destination cannot cascade.
- **Untracking files with personal content (R0).** They remain in git history; removal from history
  is a separate, force-push-level operation deliberately not attempted here.

If publication misbehaves after release, disable `publish.yml` and remove the destination from
`profile.toml` — generation and validation continue unaffected, since the layers are independent.

## Success Criteria

- [ ] A third party can `pip install` the package, run `profile init` in an empty directory, and
      generate artifacts from their own data with no reference to the owner's paths or identity.
- [ ] LICENSE and the full community/legal file set exist; `pyproject.toml` is publishable.
- [ ] No generator writes outside its configured output dir — enforced by a test.
- [ ] One registry drives both `profile generate all` and `generate_all`; the `portfolio_data`
      divergence is gone and app-data freshness is gated in CI.
- [ ] The test suite passes with zero real PII and does not mutate the real `output/` tree.
- [ ] `profile publish` defaults to dry-run, works with zero credentials, and reports `manual`
      destinations as pending rather than successful.
- [ ] `apps/portfolio/` is documented as a non-distributed reference consumer and still builds.
