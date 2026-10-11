"""The versioned output contract — what third parties actually build against.

A consumer writing a frontend against these artifacts needs two things this
project did not previously offer: a way to know the shape it is reading, and a
promise about when that shape changes. Without them, every consumer is coupled
to whatever the generators happened to emit on the day they integrated.

So:

- JSON artifacts carry a top-level ``schemaVersion``.
- ``output/manifest.json`` is the authoritative index for *all* artifacts,
  including Markdown and YAML, which cannot carry a field of their own.
- ``schemaVersion`` is one integer per artifact. Adding an optional field does
  **not** bump it — that preserves the use-if-present-else-fallback rule the
  project already follows, and a bump that fires on every addition trains
  consumers to ignore the number. Removing or retyping a field does bump it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from profilekit import manifest
from profilekit.context import discover_project
from profilekit.publishers.filesystem import FilesystemPublisher

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "project"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(FIXTURE_PROJECT, target)
    return target


def _generate_all(project: Path):
    from profilekit import registry

    ctx = discover_project(explicit=project)
    for run in registry.generators().values():
        run(ctx)
    return ctx


# ---------------------------------------------------------------------------
# JSON artifacts declare their shape
# ---------------------------------------------------------------------------


def test_published_json_artifacts_carry_schema_version(project: Path) -> None:
    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    plan = publisher.plan(ctx, {"destination": "app/data"})
    publisher.publish(ctx, plan)

    stamped = 0
    for path in (project / "app" / "data").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            # A JSON array has nowhere to put a top-level field. Wrapping it in
            # an object to make room would break every consumer reading it as a
            # list, so an array's version lives only in the manifest.
            continue
        assert payload.get("schemaVersion") == manifest.SCHEMA_VERSION, (
            f"{path.name} must declare schemaVersion"
        )
        stamped += 1

    assert stamped >= 3, "the object-shaped artifacts must carry the version"


def test_array_artifacts_stay_arrays(project: Path) -> None:
    """projects.json must remain a list: consumers index into it directly."""
    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))

    payload = json.loads((project / "app" / "data" / "projects.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)


def test_schema_version_is_a_single_integer() -> None:
    """Not a string, not a semver triple: one integer a consumer can compare."""
    assert isinstance(manifest.SCHEMA_VERSION, int)
    assert manifest.SCHEMA_VERSION >= 1


# ---------------------------------------------------------------------------
# The manifest indexes everything, including non-JSON
# ---------------------------------------------------------------------------


def test_manifest_is_written_after_a_full_run(project: Path) -> None:
    ctx = _generate_all(project)
    manifest.write(ctx)

    index = json.loads((ctx.output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert index["schemaVersion"] == manifest.SCHEMA_VERSION
    assert "generatedAt" not in index, (
        "a committed artifact must not carry a wall-clock value: it would report "
        "drift on every regeneration while saying nothing about content"
    )


def test_manifest_indexes_markdown_and_yaml_artifacts(project: Path) -> None:
    """The reason the manifest exists: .md and .yml cannot carry a field."""
    ctx = _generate_all(project)
    manifest.write(ctx)

    index = json.loads((ctx.output_dir / "manifest.json").read_text(encoding="utf-8"))
    names = {entry["name"] for entry in index["artifacts"]}

    assert "github-readme.md" in names
    assert "cv.yml" in names
    assert "manifest.json" not in names, "the manifest must not index itself"


def test_manifest_entries_carry_a_digest_and_size(project: Path) -> None:
    ctx = _generate_all(project)
    manifest.write(ctx)

    index = json.loads((ctx.output_dir / "manifest.json").read_text(encoding="utf-8"))
    for entry in index["artifacts"]:
        assert len(entry["sha256"]) == 64, f"{entry['name']} needs a sha256 digest"
        assert entry["bytes"] > 0
        assert entry["schemaVersion"] == manifest.SCHEMA_VERSION


def test_manifest_digests_match_the_files(project: Path) -> None:
    ctx = _generate_all(project)
    manifest.write(ctx)

    index = json.loads((ctx.output_dir / "manifest.json").read_text(encoding="utf-8"))
    for entry in index["artifacts"]:
        actual = manifest.digest_file(ctx.output_dir / entry["name"])
        assert entry["sha256"] == actual, f"{entry['name']} digest does not match its content"


def test_manifest_is_byte_identical_across_runs(project: Path) -> None:
    """Two runs over identical data must produce the same bytes, not just the same data.

    This is what lets the manifest be committed and diffed. The old design
    carried a timestamp, which made the file churn on every regeneration.
    """
    ctx = _generate_all(project)
    manifest.write(ctx)
    first = (ctx.output_dir / "manifest.json").read_bytes()

    manifest.write(ctx)
    second = (ctx.output_dir / "manifest.json").read_bytes()

    assert first == second


# ---------------------------------------------------------------------------
# The compatibility rule, encoded
# ---------------------------------------------------------------------------


BASE = {
    "type": "object",
    "required": ["name"],
    "properties": {"name": {"type": "string"}, "tech": {"type": "string"}},
}


def test_additive_optional_field_is_backward_compatible() -> None:
    """Adding an optional field must not bump the version."""
    evolved = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "tech": {"type": "string"},
            "stars": {"type": "integer"},
        },
    }
    assert manifest.is_backward_compatible(BASE, evolved)


def test_removing_a_field_is_breaking() -> None:
    evolved = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    assert not manifest.is_backward_compatible(BASE, evolved)


def test_retyping_a_field_is_breaking() -> None:
    evolved = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "integer"}, "tech": {"type": "string"}},
    }
    assert not manifest.is_backward_compatible(BASE, evolved)


def test_newly_requiring_an_existing_field_is_breaking() -> None:
    """A consumer that omitted an optional field would start failing."""
    evolved = {
        "type": "object",
        "required": ["name", "tech"],
        "properties": {"name": {"type": "string"}, "tech": {"type": "string"}},
    }
    assert not manifest.is_backward_compatible(BASE, evolved)


def test_adding_a_required_field_is_breaking() -> None:
    evolved = {
        "type": "object",
        "required": ["name", "owner"],
        "properties": {
            "name": {"type": "string"},
            "tech": {"type": "string"},
            "owner": {"type": "string"},
        },
    }
    assert not manifest.is_backward_compatible(BASE, evolved)


def test_identical_schemas_are_compatible() -> None:
    assert manifest.is_backward_compatible(BASE, dict(BASE))


# ---------------------------------------------------------------------------
# A broken contract must not pass the gate
# ---------------------------------------------------------------------------


def test_check_fails_when_the_manifest_is_missing(project: Path, monkeypatch) -> None:
    """The manifest is the contract; a run that produced none must not pass.

    Generation is held constant here on purpose: `check` regenerates before it
    validates, so a real run would simply recreate the file. The branch under
    test is "generation finished and left no manifest".
    """
    from profilekit import cli

    _generate_all(project)
    (project / "output" / "manifest.json").unlink(missing_ok=True)
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    assert cli.main(["--project", str(project), "check"]) != 0


def test_check_fails_when_a_digest_is_stale(project: Path, monkeypatch) -> None:
    """A stale digest would make `publish` skip a destination that needs writing."""
    from profilekit import cli

    ctx = _generate_all(project)
    manifest.write(ctx)
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    (ctx.output_dir / "linkedin.md").write_text("tampered\n", encoding="utf-8")

    assert cli.main(["--project", str(project), "check"]) != 0


def test_check_fails_when_the_manifest_is_malformed(project: Path, monkeypatch) -> None:
    from profilekit import cli

    ctx = _generate_all(project)
    manifest.write(ctx)
    (ctx.output_dir / "manifest.json").write_text('{"artifacts": []}\n', encoding="utf-8")
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    assert cli.main(["--project", str(project), "check"]) != 0
