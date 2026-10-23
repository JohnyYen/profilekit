"""Behavior pinned down by mutation testing of ``profilekit.scaffold``.

The existing suite proved ``init_project`` refuses to overwrite and writes
valid data. These tests kill the mutants that survived it: the exact refusal
messages, the list of written paths the CLI prints, the on-disk JSON format,
and scaffolding into a ``data/`` directory that already exists but is empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from profilekit import scaffold
from profilekit.context import CONFIG_FILENAME
from profilekit.scaffold import EXAMPLE_DATA, PROFILE_TOML, ScaffoldError, init_project


def test_returns_config_then_every_data_file_in_order(tmp_path: Path) -> None:
    written = init_project(tmp_path)

    assert written == [
        tmp_path / CONFIG_FILENAME,
        *(tmp_path / "data" / name for name in EXAMPLE_DATA),
    ]


def test_writes_config_verbatim(tmp_path: Path) -> None:
    init_project(tmp_path)

    assert (tmp_path / CONFIG_FILENAME).read_bytes() == PROFILE_TOML.encode("utf-8")


def test_data_files_are_two_space_indented_utf8_json_with_trailing_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Non-ASCII content is how a real profile looks (accents in names and
    # places); it must be written as characters, not \u escapes.
    payload = {"username": "José Núñez", "location": "Málaga"}
    monkeypatch.setitem(scaffold.EXAMPLE_DATA, "about.json", payload)

    init_project(tmp_path)

    raw = (tmp_path / "data" / "about.json").read_bytes()
    assert raw == ('{\n  "username": "José Núñez",\n  "location": "Málaga"\n}\n'.encode())


def test_an_existing_empty_data_directory_is_reused(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()

    written = init_project(tmp_path)

    assert len(written) == 1 + len(EXAMPLE_DATA)
    assert all(path.is_file() for path in written)


def test_existing_config_refusal_names_the_file(tmp_path: Path) -> None:
    config = tmp_path / CONFIG_FILENAME
    config.write_text("", encoding="utf-8")

    with pytest.raises(ScaffoldError) as excinfo:
        init_project(tmp_path)

    assert str(excinfo.value) == (
        f"{config} already exists; this directory is already a profilekit project"
    )


def test_existing_data_refusal_lists_every_conflicting_file(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "about.json").write_text("{}", encoding="utf-8")
    (data / "skills.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ScaffoldError) as excinfo:
        init_project(tmp_path)

    assert str(excinfo.value) == (
        "refusing to overwrite existing profile data: "
        f"{data / 'about.json'}, {data / 'skills.json'}"
    )
