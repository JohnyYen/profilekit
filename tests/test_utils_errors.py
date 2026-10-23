"""Tests for DataError, load_json_strict, and run() in profilekit/utils.py.

All tests in this module are RED before the corresponding additions to utils.py.
"""

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# (a) Missing file → DataError raised with file path; no sys.exit
# ---------------------------------------------------------------------------


def test_load_json_strict_missing_file_raises_data_error(tmp_path):
    """Missing data file raises DataError with the file path in message."""
    from profilekit.utils import DataError, load_json_strict

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with pytest.raises(DataError) as exc_info:
        load_json_strict("nonexistent.json", data_dir)

    assert "nonexistent.json" in str(exc_info.value)


# ---------------------------------------------------------------------------
# (b) Malformed JSON → DataError with file + parse location
# ---------------------------------------------------------------------------


def test_load_json_strict_malformed_json_raises_data_error(tmp_path):
    """Malformed JSON raises DataError mentioning the file."""
    from profilekit.utils import DataError, load_json_strict

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "bad.json").write_text("{not: valid json}", encoding="utf-8")

    with pytest.raises(DataError) as exc_info:
        load_json_strict("bad.json", data_dir)

    assert "bad.json" in str(exc_info.value)


# ---------------------------------------------------------------------------
# (c) Missing required field → DataError with file + field
# ---------------------------------------------------------------------------


def test_load_json_strict_missing_required_field_raises_data_error(tmp_path):
    """load_json_strict raises DataError when a required field is absent."""
    from profilekit.utils import DataError, load_json_strict

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_json(data_dir / "about.json", {"username": "bob"})

    with pytest.raises(DataError) as exc_info:
        load_json_strict("about.json", data_dir, required_fields=("username", "tagline"))

    err_str = str(exc_info.value)
    assert "about.json" in err_str
    assert "tagline" in err_str


@pytest.mark.parametrize("scalar", ["just a string", 42, None, True])
def test_load_json_strict_scalar_document_raises_data_error(tmp_path, scalar):
    """A data file whose top level is not an object or array is a data fault.

    The function's contract is ``dict | list``; returning a scalar would hand
    callers a value they index into, and the failure would surface far from
    the file that caused it.
    """
    from profilekit.utils import DataError, load_json_strict

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_json(data_dir / "about.json", scalar)

    with pytest.raises(DataError, match="about.json"):
        load_json_strict("about.json", data_dir)


# ---------------------------------------------------------------------------
# (d) run(main_fn) with DataError → exits 1 (no traceback)
# ---------------------------------------------------------------------------


def test_run_calls_sys_exit_1_on_data_error(monkeypatch):
    """run() catches DataError and calls sys.exit(1)."""
    from profilekit.utils import DataError, run

    exit_calls = []

    def fake_exit(code):
        exit_calls.append(code)
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)

    def bad_main():
        raise DataError("about.json", "username", "missing required field")

    with pytest.raises(SystemExit) as exc_info:
        run(bad_main)

    assert exc_info.value.code == 1
    assert exit_calls == [1]


# ---------------------------------------------------------------------------
# (e) run(main_fn) with unexpected exception → re-raises (not swallowed)
# ---------------------------------------------------------------------------


def test_run_reraises_unexpected_exception():
    """run() does NOT catch unexpected exceptions — they propagate normally."""
    from profilekit.utils import run

    def bad_main():
        raise ValueError("unexpected bug")

    with pytest.raises(ValueError, match="unexpected bug"):
        run(bad_main)


# ---------------------------------------------------------------------------
# load_json, the loader every generator uses, reports parse errors the same way
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("loader", ["load_json", "load_json_strict"])
def test_parse_error_names_the_file_line_and_column(tmp_path, loader):
    """generator-robustness: the message identifies the file and the location."""
    import profilekit.utils as utils

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "about.json").write_text('{\n  "a": 1,\n  oops\n}', encoding="utf-8")

    with pytest.raises(utils.DataError) as exc_info:
        getattr(utils, loader)("about.json", data_dir)

    assert exc_info.value.file == "about.json"
    assert str(exc_info.value).startswith("about.json: JSON parse error at line 3 column 3: ")


def test_load_json_reports_undecodable_bytes_as_a_data_error(tmp_path):
    """A file that is not UTF-8 is a data fault too, not an unexplained crash."""
    from profilekit.utils import DataError, load_json

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "about.json").write_bytes(b'{"a": "\xff"}')

    with pytest.raises(DataError) as exc_info:
        load_json("about.json", data_dir)

    assert str(exc_info.value).startswith("about.json: not valid UTF-8")
