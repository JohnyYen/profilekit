# The output data contract

This is the document to read if you are **consuming** profilekit output —
writing a frontend, a static site, a CV renderer, anything that reads the
generated artifacts. You should not need to read any Python to do that.

## What gets produced

A full `profile generate` writes these into the configured output directory:

| Artifact | Format | Produced by |
|---|---|---|
| `github-readme.md` | Markdown | `github-readme` |
| `linkedin.md` | Markdown | `linkedin` |
| `portfolio.md` | Markdown | `portfolio` |
| `cv.yml` | YAML (RenderCV) | `cv` |
| `cv.md` | Markdown | `cv` |
| `manifest.json` | JSON | the pipeline |

A `filesystem` publish destination additionally receives four JSON files —
`about.json`, `social.json`, `skills.json`, `projects.json` — shaped for
direct consumption by a frontend.

## `manifest.json` is the authoritative index

Markdown and YAML files cannot carry a version field, so the manifest is the
reference for **every** artifact, not just the JSON ones:

```json
{
  "schemaVersion": 1,
  "artifacts": [
    {
      "name": "github-readme.md",
      "generator": "github-readme",
      "schemaVersion": 1,
      "sha256": "…",
      "bytes": 4015
    }
  ]
}
```

Read `schemaVersion` first and decide whether you can handle it. The `sha256`
digests let you detect changes without diffing content — useful if you cache
or mirror the artifacts.

**The manifest carries no timestamp.** That is deliberate. It is a committed
artifact, and a wall-clock value inside a version-controlled file would make
it report a change on every regeneration while telling you nothing about
content. If you need to know *when* something was published, ask the publish
layer, not the generated file.

## Versioning rules

`schemaVersion` is a **single integer**, not a semver triple, because the only
question you are asking is "can I still read this?".

### Does not bump the version

- Adding a new **optional** field.

A consumer that ignores unknown fields keeps working. If the version bumped
on every addition, you would learn to ignore the number — which is worse than
having no number at all.

### Bumps the version

- Removing a field.
- Changing a field's type.
- Making a previously optional field required.
- Adding a new required field.

Each of those breaks a consumer that was reading the previous shape. The third
one is the subtle case: the field already existed, so the change looks
additive, but a consumer that was legitimately omitting it starts failing.

### On a major bump

Both versions are emitted for one minor release cycle, so you have a window to
migrate rather than a cliff.

## Shapes

### `about.json`

```json
{
  "schemaVersion": 1,
  "username": "Ada Lovelace",
  "tagline": "…",
  "description": "…",
  "currentFocus": [{ "title": "…", "description": "…" }],
  "whatIBuild": ["…"],
  "learningJourney": "…"
}
```

### `social.json`

```json
{
  "schemaVersion": 1,
  "github": "https://github.com/example",
  "linkedin": "https://linkedin.com/in/example",
  "email": "ada@example.com"
}
```

### `skills.json`

```json
{
  "schemaVersion": 1,
  "categories": [{ "label": "Mathematics", "details": ["Analysis"] }]
}
```

A `details` entry is either a plain string or an object with `name` and an
optional `icon` or `iconUrl`. Handle both.

### `projects.json`

```json
[
  {
    "name": "Note G",
    "description": "…",
    "tech": "Analytical Engine",
    "url": "https://example.com/note-g"
  }
]
```

This one is a **JSON array**, so it has nowhere to put a top-level field. Its
version lives in the manifest only. Wrapping it in an object to make room
would break every consumer that indexes into it as a list, which is not a
trade worth making for one field you can read elsewhere.

## Validating against the contract

The JSON Schemas ship inside the package, so you do not need a checkout:

```python
import importlib.resources as resources

schema = resources.files("profilekit.schemas") / "manifest.schema.json"
```

`profile check` validates the manifest against that schema and verifies every
digest matches its file, so a malformed contract cannot be published.
