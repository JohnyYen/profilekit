# Publication Specification

## Purpose

Defines `profile publish`, the layer that moves generated artifacts to
external destinations. Publishing is credentialed, opt-in, dry-run by
default, and isolated per destination; the core MUST function with zero
credentials configured.

## Requirements

### Requirement: profile publish with config-declared destinations and capability

`profile publish [dest|all]` MUST publish only destinations declared in
`profile.toml`. Each destination MUST declare its capability: `push` (the
tool performs the write) or `manual` (a human performs it).

#### Scenario: Publish a single declared destination

- GIVEN `profile.toml` declares a destination named `github-readme`
- WHEN `profile publish github-readme` runs
- THEN only that destination SHALL be published
- AND undeclared destinations SHALL NOT be touched

#### Scenario: Publish all declared destinations

- GIVEN `profile.toml` declares multiple destinations
- WHEN `profile publish all` runs
- THEN every declared destination SHALL be attempted

### Requirement: Dry-run is the default

`profile publish` MUST default to dry-run: it reports what would change
without performing any write or network call. An explicit flag (e.g.
`--live`) MUST be required to perform a real publish.

#### Scenario: Default invocation performs no writes

- GIVEN a destination is configured with valid credentials
- WHEN `profile publish` runs without an explicit live flag
- THEN no external write SHALL occur
- AND the report SHALL state what would have changed
- AND a `push` destination SHALL be marked `would-publish`, never `skipped`,
  which is reserved for a destination missing its credential

#### Scenario: Explicit live flag performs the write

- GIVEN the same configuration
- WHEN `profile publish --live` runs
- THEN the destination SHALL receive the real write

### Requirement: manual destinations never report success

A `manual`-capability destination MUST emit its artifact and report a
pending action. It MUST NOT report `success` for a write it did not itself
perform.

#### Scenario: Manual destination reports pending

- GIVEN a destination declares `capability = "manual"` (e.g. LinkedIn)
- WHEN it is published (dry-run or live)
- THEN the report SHALL mark it `pending`, never `success`
- AND the artifact intended for manual action SHALL be written to the
  configured location

### Requirement: Content-hash idempotency for push destinations

A `push` destination MUST skip the write when the content hash of the
artifact matches the hash last successfully published to that destination.

#### Scenario: Unchanged content is not republished

- GIVEN a destination's last published content hash matches the current
  artifact's hash
- WHEN `profile publish --live` runs for that destination
- THEN no write SHALL be performed
- AND the report SHALL state the destination is up to date

#### Scenario: Changed content is republished

- GIVEN the artifact's content hash differs from the last published hash
- WHEN `profile publish --live` runs
- THEN the write SHALL be performed
- AND the new hash SHALL be recorded

### Requirement: Failure isolation across destinations

A failure publishing one destination MUST NOT prevent other destinations
from being attempted in the same run. `profile publish all` MUST report
per-destination outcomes and exit non-zero if any destination failed.

#### Scenario: One destination fails, others proceed

- GIVEN two destinations are configured and one raises an error during
  publish
- WHEN `profile publish all --live` runs
- THEN the failing destination SHALL be reported as failed
- AND the other destination SHALL still be attempted and reported
  independently

### Requirement: Zero-credential core

`profile publish` MUST run without a fatal error when no destination
credentials are configured. Destinations missing required credentials MUST
be skipped with a log message, not treated as a fatal error.

#### Scenario: No credentials configured anywhere

- GIVEN no destination has credentials configured
- WHEN `profile publish all` runs
- THEN the command SHALL complete without a fatal error
- AND each destination SHALL be reported as skipped, with a log line naming
  the missing credential

### Requirement: CI publish workflow gated and isolated from validation

A CI workflow MUST run `profile check` and a `profile publish` dry run on
pushes to `main`, gated so it proceeds only when the configured output
directory changed in that push. It MUST NOT write to a destination on a push;
an explicit manual dispatch MUST be required for that.

Absent per-destination secrets MUST cause that destination to be skipped with
a log entry, not a failed run. This workflow MUST be separate from the
validation workflow, and the validation workflow MUST NOT publish.

> Amended by owner decision after verification. The original wording required
> publishing on push. Both destination kinds that ship with the package write
> locally — `filesystem` into a directory inside the project, `manual` by
> handing work to a human — and on a runner the project directory is a
> throwaway checkout discarded when the job ends. Publishing on push would
> therefore report destinations as published while nothing durable changed,
> which is the precise failure the `manual` capability exists to avoid. CI's
> answerable question is whether the committed destinations are current, which
> `profile check` decides; publishing a filesystem destination happens locally
> and is then committed.

#### Scenario: Push without output changes does not publish

- GIVEN a push to `main` that does not modify the output directory
- WHEN CI evaluates the publish workflow
- THEN the publish job SHALL NOT run

#### Scenario: Missing destination secret skips, does not fail

- GIVEN a push to `main` changes the output directory and one destination's
  secret is absent
- WHEN the publish workflow runs
- THEN that destination SHALL be skipped with a logged reason
- AND the workflow SHALL NOT fail solely because of the missing secret

#### Scenario: Validation workflow never publishes

- GIVEN the validation workflow (`validate.yml`) runs on a pull request
- WHEN it completes
- THEN no destination SHALL have been published to

#### Scenario: Manual dry-run dispatch

- GIVEN a maintainer triggers the publish workflow via `workflow_dispatch`
- WHEN no explicit live override is provided
- THEN the workflow SHALL run in dry-run mode
