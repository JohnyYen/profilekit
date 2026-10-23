"""The versioned output contract — what third parties actually build against.

A consumer writing a frontend against these artifacts needs two things this
project did not previously offer: a way to know the shape it is reading, and a
promise about when that shape changes. Without them, every consumer is coupled
to whatever the generators happened to emit on the day they integrated.

So:

- JSON artifacts carry a top-level ``schemaVersion``.
- ``output/manifest.json`` indexes *every* artifact in ``output/``,
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


def test_manifest_skips_hidden_files(project: Path) -> None:
    """Dotfiles are tooling noise, never artifacts.

    A `.gitkeep`, an editor swap file or a `.DS_Store` in the output directory
    used to be indexed as an artifact, so the committed contract depended on
    whose machine last ran the generators.
    """
    ctx = _generate_all(project)
    for stray in (".gitkeep", ".DS_Store", ".cv.md.swp"):
        (ctx.output_dir / stray).write_text("noise\n", encoding="utf-8")

    names = {entry["name"] for entry in manifest.build(ctx.output_dir)["artifacts"]}

    assert names == set(manifest.ARTIFACT_GENERATORS)


def test_manifest_indexes_a_plugin_artifact_as_unattributed(project: Path) -> None:
    """A third-party generator's artifact is part of the output set.

    Generators do not declare what they write, so a name the package does not
    know is indexed with generator "unknown" rather than dropped — dropping it
    would leave a plugin's output outside the contract.
    """
    ctx = _generate_all(project)
    (ctx.output_dir / "plugin-card.txt").write_text("plugin card\n", encoding="utf-8")

    entries = {e["name"]: e for e in manifest.build(ctx.output_dir)["artifacts"]}

    assert entries["plugin-card.txt"]["generator"] == "unknown"
    assert entries["cv.yml"]["generator"] == "cv"


def test_manifest_does_not_follow_a_symlink_out_of_the_output_directory(
    project: Path, tmp_path: Path
) -> None:
    """A symlink in output/ is not an artifact, wherever it points.

    Generators never create links, and the publisher refuses to follow one,
    so indexing a link would put a file outside the project into the
    committed contract: its name, size and digest.
    """
    ctx = _generate_all(project)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("not part of the profile\n", encoding="utf-8")
    try:
        (ctx.output_dir / "linked.txt").symlink_to(outside)
    except OSError:
        pytest.skip("this platform cannot create symlinks")

    names = {entry["name"] for entry in manifest.build(ctx.output_dir)["artifacts"]}

    assert "linked.txt" not in names
    assert names == set(manifest.ARTIFACT_GENERATORS)


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


def test_check_fails_when_the_manifest_is_missing(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
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

    assert cli.main(["--project", str(project), "check"]) == 1
    captured = capsys.readouterr()
    assert "error: output/manifest.json is missing — run `profile generate`" in captured.err
    assert "check passed" not in captured.out


def test_check_fails_when_the_manifest_is_malformed(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from profilekit import cli

    ctx = _generate_all(project)
    manifest.write(ctx)
    (ctx.output_dir / "manifest.json").write_text('{"artifacts": []}\n', encoding="utf-8")
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    assert cli.main(["--project", str(project), "check"]) == 1
    captured = capsys.readouterr()
    assert "error: manifest.json: <root>: 'schemaVersion' is a required property" in captured.err
    assert "check passed" not in captured.out


# ---------------------------------------------------------------------------
# Published artifacts validate against their OWN schemas
# ---------------------------------------------------------------------------


def test_every_published_artifact_has_a_schema() -> None:
    """The output shapes are a contract, so they need schemas of their own.

    The schemas under `data/` validate the *input*. Validating published files
    against those passes only because they allow additional properties, so a
    transform could drop a required field and nothing would notice.
    """
    from profilekit import cli
    from profilekit.validate import packaged_schemas

    schemas = packaged_schemas()
    for filename, schema_name in cli.PUBLISHED_SCHEMAS.items():
        assert (schemas / schema_name).is_file(), f"{filename} has no published schema"


def test_published_artifacts_validate_against_their_schemas(project: Path) -> None:
    import jsonschema

    from profilekit import cli
    from profilekit.validate import packaged_schemas

    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))

    schemas = packaged_schemas()
    checked = 0
    for filename, schema_name in cli.PUBLISHED_SCHEMAS.items():
        artifact = project / "app" / "data" / filename
        schema = json.loads((schemas / schema_name).read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(
            json.loads(artifact.read_text(encoding="utf-8"))
        )
        checked += 1

    # The four published files plus the destination manifest that versions them.
    assert checked == 5


def test_check_fails_when_a_published_artifact_breaks_its_schema(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Isolate the schema gate from the destination-drift gate.

    Breaking a published shape necessarily makes it differ from what the
    publisher would write, so the earlier drift gate fires first and an
    exit-code assertion proves nothing about the schema check — this test
    passed twice while the schema gate could have been deleted. The drift
    probe is therefore stubbed out, leaving only the schema gate to fail.
    """
    from profilekit import cli

    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))
    _generate_all(project)
    manifest.write(ctx)

    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)
    # The gate under test is the only one left that can fail.
    monkeypatch.setattr(cli, "_stale_published_destinations", lambda ctx: [])
    monkeypatch.setattr(
        cli,
        "filesystem_destinations",
        lambda ctx: [{"kind": "filesystem", "destination": "app/data"}],
    )

    broken = project / "app" / "data" / "about.json"
    broken.write_text('{"schemaVersion": 1}\n', encoding="utf-8")

    rc = cli.main(["--project", str(project), "check"])
    assert rc == 1, "the schema gate did not fire"
    captured = capsys.readouterr()
    assert "error: published about.json: <root>: 'username' is a required property" in captured.err
    assert "check passed" not in captured.out


def test_the_schema_gate_is_the_only_thing_failing_in_that_test(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Prove the isolation holds: with a valid shape and drift stubbed, check passes."""
    from profilekit import cli

    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))
    _generate_all(project)
    manifest.write(ctx)

    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)
    monkeypatch.setattr(cli, "_stale_published_destinations", lambda ctx: [])
    monkeypatch.setattr(
        cli,
        "filesystem_destinations",
        lambda ctx: [{"kind": "filesystem", "destination": "app/data"}],
    )

    assert cli.main(["--project", str(project), "check"]) == 0
    captured = capsys.readouterr()
    assert "check passed: data valid, output/ up to date, destinations current" in captured.out
    assert "error:" not in captured.err


def test_the_schema_gate_names_the_offending_field(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A gate that fails without saying what broke is barely a gate."""
    from profilekit import cli

    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))
    _generate_all(project)
    manifest.write(ctx)

    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)
    monkeypatch.setattr(cli, "_stale_published_destinations", lambda ctx: [])
    monkeypatch.setattr(
        cli,
        "filesystem_destinations",
        lambda ctx: [{"kind": "filesystem", "destination": "app/data"}],
    )

    (project / "app" / "data" / "about.json").write_text('{"schemaVersion": 1}\n', encoding="utf-8")
    assert cli.main(["--project", str(project), "check"]) == 1

    err = capsys.readouterr().err
    for field in ("username", "tagline", "description"):
        assert f"error: published about.json: <root>: '{field}' is a required property" in err


def test_published_schemas_resolve_even_with_a_project_schemas_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A project may point `[paths] schemas` at its own directory.

    Published schemas describe this tool's output, so they must come from the
    package regardless. Reading them through the project override raised an
    unhandled FileNotFoundError for any project that set one — the schemas
    only ever exist inside the distribution.
    """
    import shutil as _shutil

    from profilekit import cli

    target = tmp_path / "p"
    _shutil.copytree(FIXTURE_PROJECT, target)
    (target / "my-schemas").mkdir()
    (target / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[paths]\nschemas = "my-schemas"\n\n'
        '[generators.cv]\ncurrent_date = "2000-01-01"\n\n'
        '[publishers.site]\nkind = "filesystem"\ndestination = "app/data"\n',
        encoding="utf-8",
    )

    _generate_all(target)
    ctx = discover_project(explicit=target)
    assert ctx.schemas_dir is not None, "the override must be in effect for this test"

    manifest.write(ctx)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))

    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    assert cli.main(["--project", str(target), "check"]) == 0
    captured = capsys.readouterr()
    assert "check passed: data valid, output/ up to date, destinations current" in captured.out
    assert "error:" not in captured.err


# ---------------------------------------------------------------------------
# The destination manifest — the version of the array-shaped projects.json
# ---------------------------------------------------------------------------


def _isolate_published_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub every earlier gate so only the published-artifact gate can fail."""
    from profilekit import cli

    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)
    monkeypatch.setattr(cli, "_stale_published_destinations", lambda ctx: [])
    monkeypatch.setattr(
        cli,
        "filesystem_destinations",
        lambda ctx: [{"kind": "filesystem", "destination": "app/data"}],
    )


def _publish_and_generate(project: Path) -> Path:
    ctx = discover_project(explicit=project)
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "app/data"}))
    _generate_all(project)
    manifest.write(ctx)
    return project / "app" / "data"


def test_the_destination_manifest_carries_the_projects_json_version(project: Path) -> None:
    """output-data-contract: an array artifact's version is readable next to it."""
    data = _publish_and_generate(project)
    assert isinstance(json.loads((data / "projects.json").read_text(encoding="utf-8")), list)

    index = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in index["files"]}
    assert entries["projects.json"]["schemaVersion"] == manifest.SCHEMA_VERSION


def test_the_destination_manifest_schema_refuses_a_self_entry() -> None:
    """A manifest that indexes itself can never hold its own correct digest."""
    import jsonschema

    from profilekit.validate import packaged_schemas

    schema = json.loads(
        (packaged_schemas() / "published-manifest.schema.json").read_text(encoding="utf-8")
    )
    entry = {"schemaVersion": 1, "sha256": "0" * 64, "bytes": 1}
    validator = jsonschema.Draft7Validator(schema)

    assert validator.is_valid({"schemaVersion": 1, "files": [{"name": "about.json", **entry}]})
    assert not validator.is_valid(
        {"schemaVersion": 1, "files": [{"name": "manifest.json", **entry}]}
    )
    assert not validator.is_valid({"schemaVersion": 1, "files": [{"name": "../x.json", **entry}]})


def test_check_fails_when_a_destination_digest_does_not_match_its_file(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A schema-valid edit to a published file still breaks the manifest's promise."""
    from profilekit import cli

    data = _publish_and_generate(project)
    _isolate_published_gate(monkeypatch)
    about = json.loads((data / "about.json").read_text(encoding="utf-8"))
    about["username"] = "someone-else"
    (data / "about.json").write_text(json.dumps(about) + "\n", encoding="utf-8")

    assert cli.main(["--project", str(project), "check"]) == 1
    err = capsys.readouterr().err
    assert "error: published manifest.json digest for about.json does not match its content" in err


def test_check_fails_when_a_destination_manifest_lists_a_missing_file(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from profilekit import cli

    data = _publish_and_generate(project)
    _isolate_published_gate(monkeypatch)
    (data / "skills.json").unlink()

    assert cli.main(["--project", str(project), "check"]) == 1
    err = capsys.readouterr().err
    assert "error: published manifest.json lists missing file skills.json" in err


def test_check_fails_when_the_destination_manifest_breaks_its_schema(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from profilekit import cli

    data = _publish_and_generate(project)
    _isolate_published_gate(monkeypatch)
    (data / "manifest.json").write_text('{"files": []}\n', encoding="utf-8")

    assert cli.main(["--project", str(project), "check"]) == 1
    err = capsys.readouterr().err
    assert "error: published manifest.json: <root>: 'schemaVersion' is a required property" in err
