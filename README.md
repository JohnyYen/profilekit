# profilekit

Keep your professional profile in one place, generate every published surface
from it.

You write your profile once as structured JSON. `profilekit` turns it into a
GitHub profile README, LinkedIn copy, a CV, and JSON for whatever frontend you
use — then optionally publishes each one to where it belongs.

The problem it solves is drift. A profile lives in five places that disagree:
the README says one thing, LinkedIn another, the CV is six months stale, and
the portfolio was last touched when you built it. Editing five surfaces by
hand is how they get out of sync, and nobody notices until a recruiter reads
the wrong one.

## Quick start

```sh
pip install profilekit

mkdir my-profile && cd my-profile
profile init          # scaffolds profile.toml and example data
profile validate      # checks your data against the schemas
profile generate      # writes output/
```

`profile init` seeds a complete example profile so you can see the shape
before you write your own. Edit `data/*.json`, run `profile generate` again,
and every artifact updates together.

## Commands

| Command | What it does |
|---|---|
| `profile init [dir]` | Scaffold a new project with example data |
| `profile generate [target]` | Generate one target or all of them |
| `profile list` | List the registered generation targets |
| `profile validate` | Validate your data against the JSON Schemas |
| `profile check` | Validate, regenerate, and verify nothing is stale |
| `profile publish [dest] [--execute]` | Publish to configured destinations |

Every command takes `--project DIR` to act on a project other than the one
containing the working directory, or reads `PROFILEKIT_PROJECT`.

## Generating

`data/*.json` is the only thing you hand-write. Everything under `output/` is
produced from it:

| Artifact | Use |
|---|---|
| `github-readme.md` | Your GitHub profile README |
| `linkedin.md` | Copy to paste into LinkedIn |
| `cv.yml` | A [RenderCV](https://github.com/rendercv/rendercv) document |
| `cv.md` | The same CV, readable |
| `manifest.json` | Index of every artifact, with digests and version |

## Publishing

Generating and publishing are separate on purpose. A generator is pure — data
in, artifacts into one directory, no network, no credentials. A publisher
carries those artifacts somewhere the project does not own.

Declare destinations in `profile.toml`:

```toml
[publishers.site-data]
kind = "filesystem"
destination = "site/src/data"

[publishers.linkedin]
kind = "manual"
artifacts = ["linkedin.md"]
```

```sh
profile publish              # dry run: shows what would happen
profile publish --execute    # actually publish
```

**Dry run is the default.** Publishing is outward-facing and not reliably
reversible, so writing is something you opt into.

Two destination kinds ship with the package and need no credentials:

- **`filesystem`** writes into a directory inside your project — point it at
  whatever frontend reads the JSON.
- **`manual`** is for platforms with no write API. LinkedIn is the example:
  it offers no programmatic access to profile fields without partner-level
  approval. A `manual` destination emits its artifact and tells you what is
  left to do. It never reports success for something it did not do, because a
  tool that claims a publish it did not perform is how a profile goes stale
  without anyone noticing.

Credentialed destinations install separately as plugins. The core declares no
network dependency at all.

## Consuming the output

If you are writing a frontend against the generated data, read
[`docs/data-contract.md`](docs/data-contract.md). It specifies every shape, the
`schemaVersion` policy, and which changes are safe versus breaking — so you do
not have to read any Python to integrate.

## Extending it

Generators and publishers are discovered through entry points, so adding one
is a registration rather than a fork:

```toml
[project.entry-points."profilekit.generators"]
my-target = "my_package.my_module:main"
```

See [`docs/authoring-generators.md`](docs/authoring-generators.md) and
[`docs/authoring-publishers.md`](docs/authoring-publishers.md).

## Development

```sh
git clone https://github.com/JohnyYen/profile-data
cd profile-data
uv sync --extra dev      # or: pip install -e '.[dev]'

pytest -q                # tests, with an 80% coverage gate
ruff check . && ruff format --check .
mypy
pre-commit install       # optional; no uv required
```

CI runs lint, types, tests, data validation, and an `output/` freshness gate.

## This repository is also a project

`data/` holds the maintainer's real profile, and `apps/portfolio/` is his own
portfolio — kept here as a worked example of consuming the output contract,
deliberately not part of the distributed package. The package does not install
either. Treat them as the reference implementation they are: useful to read,
not something you inherit.

## Release checklist (maintainer)

The code is complete; the distribution is not. Until these steps are done,
`pip install profilekit` does not work for anyone. Do them in order — the
PyPI step is irreversible.

1. **Merge the work.** Push `feat/open-source-release`, open a pull request to
   `main`, and merge it once CI (`.github/workflows/validate.yml`) is green.
2. **Set up trusted publishing** (no API token is stored anywhere). On both
   [PyPI](https://pypi.org/manage/account/publishing/) and
   [TestPyPI](https://test.pypi.org/manage/account/publishing/), add a pending
   publisher for project `profilekit` with owner `JohnyYen`, repository
   `profile-data`, workflow `release.yml`, and environment `pypi` (on PyPI) or
   `testpypi` (on TestPyPI).
3. **Create the GitHub environments.** In the repository settings, under
   Environments, create `testpypi` and `pypi`. Give `pypi` a required
   reviewer (yourself), so the irreversible upload waits for your approval.
4. **Check the version.** `pyproject.toml` declares the version that will be
   claimed on PyPI. The release workflow refuses a tag that does not match it.
5. **Tag the release** from an up-to-date `main`:

   ```sh
   git tag v0.1.0
   git push origin v0.1.0
   ```

   `.github/workflows/release.yml` then runs the quality gates, builds,
   smoke-tests the wheel outside any checkout, uploads to TestPyPI, and waits
   for your approval before uploading to PyPI.
6. **Verify as a stranger would**, in a fresh virtual environment outside this
   repository:

   ```sh
   pip install profilekit
   profile init
   profile validate
   profile generate
   ```

7. **Fix the broken CV link.** The `cvUrl` in `data/social.json` returns
   HTTP 404. Either publish the `cv-latest` release asset in the CV repository
   or point `cvUrl` at a file that exists, then run `profile validate` (it
   checks links) and `profile check` before committing.

## License

MIT. See [LICENSE](LICENSE).
