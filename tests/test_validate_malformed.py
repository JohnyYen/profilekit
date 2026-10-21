"""validate.main on data files that are not JSON at all.

`validate_file` already turns a parse error into a FAIL line. The cross-file
check and the reachability probes read the same files again afterwards, so a
malformed file must not reach them as an exception either — the user is owed
the FAIL line naming the file and a non-zero exit, never a traceback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import profilekit.validate as validate
from profilekit.context import ProjectContext
from profilekit.scaffold import init_project


@pytest.fixture
def scaffolded(tmp_path: Path, monkeypatch) -> ProjectContext:
    """A project holding the valid example data, with both probes offline."""
    monkeypatch.setenv("SKIP_ICON_CHECK", "1")
    monkeypatch.setenv("SKIP_LINK_CHECK", "1")
    init_project(tmp_path)
    return ProjectContext.for_root(tmp_path)


def test_the_example_data_passes(scaffolded: ProjectContext, capsys) -> None:
    """The control: the files below fail because of the edit, not the fixture."""
    assert validate.main(scaffolded) == 0
    assert "All validations passed!" in capsys.readouterr().out


@pytest.mark.parametrize("filename", ["about.json", "skills.json", "projects.json", "social.json"])
def test_malformed_file_is_a_named_failure_not_an_exception(
    scaffolded: ProjectContext, capsys, filename: str
) -> None:
    (scaffolded.data_dir / filename).write_text("{not json", encoding="utf-8")

    code = validate.main(scaffolded)

    out = capsys.readouterr()
    assert code == 1
    assert f"{filename}: JSON parse error" in out.out
    assert "FAIL" in out.out
    assert "Some validations FAILED!" in out.out


def test_malformed_schema_override_names_the_schema(tmp_path: Path) -> None:
    """A broken project schema is the schema's fault, not the data file's."""
    init_project(tmp_path)
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "about.schema.json").write_text("{not json", encoding="utf-8")
    ctx = ProjectContext.for_root(tmp_path, schemas_dir=schemas)

    passed, errors = validate.validate_file("about.json", ctx)

    assert passed is False
    assert errors[0].startswith("about.schema.json: JSON parse error in schema")
