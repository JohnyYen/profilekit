# Output Data Contract Specification

## Purpose

Defines the versioned, documented, publicly referenceable shape of artifacts
synced to external consumers (starting with the portfolio app's JSON files)
— the part of this system a third party actually depends on.

## Requirements

### Requirement: schemaVersion on emitted artifacts

Every JSON artifact emitted for external consumption MUST declare the
contract version it conforms to. A consumer MUST be able to detect a version
mismatch without parsing the rest of the payload.

An **object-shaped** artifact MUST carry a top-level `schemaVersion` field.
An **array-shaped** artifact has nowhere to put one, and MUST declare its
version through a manifest instead: the `manifest.json` the publisher writes
into the same destination, next to the artifact.

#### Scenario: An object artifact carries its version inline

- GIVEN a publisher emits a JSON object for an external consumer
- WHEN the artifact is inspected
- THEN it SHALL include a top-level `schemaVersion` field with the current
  contract version

#### Scenario: An array artifact declares its version in the manifest

- GIVEN a publisher emits a JSON array for an external consumer
- WHEN the artifact is inspected
- THEN it SHALL remain an array
- AND the destination's `manifest.json` SHALL carry the contract version for it

> Amended by owner decision after verification. The original wording required
> every JSON artifact to carry the field inline, which `projects.json` cannot
> satisfy without being wrapped in an object. Wrapping it would break every
> consumer that indexes into it as a list — including this repository's own
> portfolio app — to gain a field already readable from the manifest. The
> manifest exists precisely because Markdown and YAML artifacts cannot carry a
> version either; an array is the same case.
>
> Amended again by owner decision (2026-10-20): `output/manifest.json` indexes
> only `output/`, and a consumer reads the publish destination, so the version
> lives in a manifest the filesystem publisher writes into that destination.

#### Scenario: Version bump on breaking change

- GIVEN a breaking change is made to an artifact's shape
- WHEN the artifact is next emitted
- THEN `schemaVersion` SHALL be incremented
- AND the change SHALL be documented in the artifact's schema/reference doc

### Requirement: Documented, referenceable schema per artifact

Each emitted artifact type MUST have a corresponding JSON Schema file,
packaged with the distribution and referenceable by a stable path or
published URL. The documented shape MUST match the schema exactly.

#### Scenario: Schema resolves for a given artifact

- GIVEN an emitted artifact's `schemaVersion`
- WHEN a consumer looks up the matching schema
- THEN a JSON Schema file for that exact version SHALL exist at a
  documented, stable location

#### Scenario: Emitted artifact validates against its own schema

- GIVEN any artifact emitted by a publisher
- WHEN it is validated against the schema matching its `schemaVersion`
- THEN validation SHALL pass

### Requirement: Backward compatibility within a major version

Within the same major `schemaVersion`, new fields MUST be additive and
optional; existing fields MUST NOT be removed or retyped. Consumers built
against an older minor version MUST continue to parse artifacts of a newer
minor version.

#### Scenario: Additive field does not break older consumers

- GIVEN a new optional field is added within the same major version
- WHEN a consumer written against the prior minor version parses the new
  artifact
- THEN it SHALL parse successfully, ignoring the unknown field

#### Scenario: Breaking change requires a major bump

- GIVEN a field is removed or its type changed
- WHEN the artifact is next emitted
- THEN the major component of `schemaVersion` SHALL be incremented
