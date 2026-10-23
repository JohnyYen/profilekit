"""Behavior pinned down by mutation testing of ``profilekit.utils``.

These helpers turn a data fault into the one line a user reads before fixing
their JSON. Each test kills mutants that survived the baseline run (see
``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from profilekit.utils import (
    DataError,
    load_json,
    load_json_strict,
    run,
    skill_icon,
    what_i_build,
    write_output,
)


def test_data_error_keeps_file_and_field() -> None:
    error = DataError("about.json", field="username", message="missing required field")

    assert (error.file, error.field) == ("about.json", "username")
    assert str(error) == "about.json (field: 'username'): missing required field"


def test_data_error_without_a_message_is_just_the_location() -> None:
    assert str(DataError("about.json", field="username")) == "about.json (field: 'username')"
    assert str(DataError("about.json")) == "about.json"


def test_strict_load_of_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(DataError) as excinfo:
        load_json_strict("about.json", tmp_path)

    assert str(excinfo.value) == "about.json: data file not found"


def test_strict_load_names_the_missing_field(tmp_path: Path) -> None:
    (tmp_path / "about.json").write_text('{"tagline": "x"}', encoding="utf-8")

    with pytest.raises(DataError) as excinfo:
        load_json_strict("about.json", tmp_path, required_fields=("tagline", "username"))

    assert excinfo.value.field == "username"
    assert str(excinfo.value) == "about.json (field: 'username'): missing required field"


def test_required_fields_are_not_checked_against_a_list(tmp_path: Path) -> None:
    (tmp_path / "projects.json").write_text('[{"name": "a"}]', encoding="utf-8")

    data = load_json_strict("projects.json", tmp_path, required_fields=("name",))

    assert data == [{"name": "a"}]


def test_run_prints_a_data_error_to_stderr_and_exits_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail() -> None:
        raise DataError("about.json", message="boom")

    with pytest.raises(SystemExit) as excinfo:
        run(fail)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.err == "about.json: boom\n"
    assert captured.out == ""


def test_load_json_reports_a_missing_file_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        load_json("about.json", tmp_path)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.err == "ERROR: Missing data file: about.json\n"
    assert captured.out == ""


def test_write_output_creates_nested_directories_and_writes_exact_text(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"

    path = write_output("héllo\n", target, "out.md")

    assert path == target / "out.md"
    assert path.read_bytes() == "héllo\n".encode()


def test_variants_that_are_not_a_mapping_fall_back_to_the_generic_list() -> None:
    about = {"whatIBuildVariants": ["oops"], "whatIBuild": ["Tools"]}

    assert what_i_build(about, "linkedin") == ["Tools"]


def test_a_list_variant_is_returned_as_its_items() -> None:
    about = {"whatIBuildVariants": {"linkedin": ["APIs", "CLIs"]}, "whatIBuild": ["Tools"]}

    assert what_i_build(about, "linkedin") == ["APIs", "CLIs"]


def test_an_empty_icon_slug_means_no_icon() -> None:
    assert skill_icon({"name": "Go", "icon": ""}) == (None, None)


def test_load_json_strict_parses_valid_json(tmp_path: Path) -> None:
    (tmp_path / "skills.json").write_text(json.dumps({"categories": []}), encoding="utf-8")

    assert load_json_strict("skills.json", tmp_path) == {"categories": []}
