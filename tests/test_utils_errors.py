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
