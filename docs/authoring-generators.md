# Writing a generator

A generator turns canonical profile data into one artifact. That is the whole
job, and the constraints are what make it safe to run:

- **Pure.** No network, no credentials, no reading the environment.
- **One destination.** It writes only inside the output directory it was
  given.
- **Deterministic.** The same data produces the same bytes, so output can be
  committed and diffed.

Anything that needs to reach outside the project is a *publisher*, not a
generator. See [`authoring-publishers.md`](authoring-publishers.md).

## The contract

```python
from pathlib import Path

from profilekit.context import ProjectContext, discover_project
from profilekit.utils import load_json, write_output


def main(ctx: ProjectContext | None = None, output_dir: Path | None = None) -> None:
    ctx = ctx or discover_project()
    out_dir = output_dir or ctx.output_dir

    about = load_json("about.json", ctx.data_dir)

    content = render(about)
    write_output(content, out_dir, "my-artifact.md")
```

`ctx` carries the project's resolved directories. `ctx or discover_project()`
lets the function work both as a registry entry point and when called
directly.

`output_dir` overrides the context's output directory. Accept it: it is how
tests redirect writes without monkeypatching, and how the output-boundary test
proves your generator stays inside its lane.

## Registering

```toml
[project.entry-points."profilekit.generators"]
my-target = "my_package.my_module:main"
```

That is the entire integration. There is one registry and no list to edit, so
your target appears in `profile list` and `profile generate` with no change to
profilekit itself.

The name is what users type: `profile generate my-target`.

> This matters more than it looks. profilekit previously kept generation
> targets in two hardcoded lists that were expected to agree. They diverged,
> one command silently skipped a step the other ran, and CI did not notice
> because it drove the path that was missing it. Entry points mean there is
> nothing to keep in sync.

## Configuration

Read your options from the context, never from a module constant:

```python
options = ctx.generator_options("my-target")
greeting = options.get("greeting", DEFAULT_GREETING)
```

```toml
[generators.my-target]
greeting = "Hello, {name}"
```

Unknown keys inside your table are passed through untouched — the core does
not gatekeep options it knows nothing about, so you own validating your own.

**Give every option a default that reproduces your current output.** An
option whose absence changes what users already have is a breaking change
wearing a feature's clothes.

## Determinism

Never put a wall-clock value in a generated artifact. It makes the output
different on every run, which destroys the ability to commit it and diff it,
and tells a reader nothing about content. If a date genuinely belongs in the
artifact, take it from configuration so a project can pin it.

## Testing

Three tests are worth writing, and the project's own suite enforces the first
two for shipped generators:

```python
def test_writes_only_inside_the_given_output_dir(tmp_path):
    main(ctx, output_dir=tmp_path / "output")
    escaped = [
        p for p in tmp_path.rglob("*") if p.is_file() and (tmp_path / "output") not in p.parents
    ]
    assert not escaped


def test_output_is_byte_identical_across_runs(tmp_path): ...  # run twice, compare bytes


def test_a_golden_snapshot_matches(tmp_path): ...  # compare against a committed reference file
```

Point tests at a fixture project rather than real profile data. A golden bound
to live data breaks every time the content changes, which trains people to
regenerate snapshots without reading the diff.
