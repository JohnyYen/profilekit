"""Behavior pinned down by mutation testing of ``profilekit.manifest``.

``output/manifest.json`` is a committed file that third parties read, so its
byte format is part of the contract: a change in indentation or escaping shows
up as drift in every project. Each test kills mutants that survived the
baseline run (see ``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from profilekit import manifest
from profilekit.context import ProjectContext


def test_manifest_is_two_space_json_with_literal_unicode_and_trailing_newline(
    tmp_path: Path,
) -> None:
    ctx = ProjectContext.for_root(tmp_path)
    ctx.output_dir.mkdir()
    (ctx.output_dir / "café.md").write_bytes(b"x")
    digest = hashlib.sha256(b"x").hexdigest()

    path = manifest.write(ctx)

    assert (
        path.read_bytes()
        == (
            "{\n"
            '  "schemaVersion": 1,\n'
            '  "artifacts": [\n'
            "    {\n"
            '      "name": "café.md",\n'
            '      "generator": "unknown",\n'
            '      "schemaVersion": 1,\n'
            f'      "sha256": "{digest}",\n'
            '      "bytes": 1\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ).encode()
    )


def test_manifest_write_creates_a_nested_output_directory(tmp_path: Path) -> None:
    ctx = ProjectContext.for_root(tmp_path, output_dir=tmp_path / "build" / "profile" / "out")

    path = manifest.write(ctx)

    assert manifest.read(ctx.output_dir) == {"schemaVersion": 1, "artifacts": []}
    assert path == tmp_path / "build" / "profile" / "out" / "manifest.json"


def test_schemas_without_properties_are_compatible() -> None:
    assert manifest.is_backward_compatible({}, {}) is True
    assert manifest.is_backward_compatible({"properties": None}, {"properties": []}) is True


def test_schemas_without_required_lists_are_compatible() -> None:
    before = {"properties": {"a": {"type": "string"}}}
    after = {"properties": {"a": {"type": "string"}}, "required": "a"}

    assert manifest.is_backward_compatible(before, before) is True
    assert manifest.is_backward_compatible(before, after) is True
