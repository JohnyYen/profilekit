"""Integration tests for the jsonschema-backed validate.py.

All four scenarios must fail before the validate.py rewrite (current
hand-rolled validator does not enforce oneOf or required fields inside
nested items).
"""

import importlib.resources
import json
from pathlib import Path

import profilekit.validate as validate

# Schemas are packaged data (src/profilekit/schemas/), not a repo-relative
# path — resolve the same way the production code does.
SCHEMAS_DIR = importlib.resources.files("profilekit.schemas")


def _write_data_dir(tmp_path: Path, filename: str, data: object) -> Path:
    """Write *data* as *filename* inside a fresh tmp data dir; return the dir."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / filename).write_text(json.dumps(data), encoding="utf-8")
    return data_dir


# ---------------------------------------------------------------------------
# (a) Type violation → FAIL with field mentioned in error
# ---------------------------------------------------------------------------


def test_type_violation_fails(monkeypatch, tmp_path):
    """A string value where an array is required must be rejected (type enforcement)."""
    bad_about = {
        "username": "testuser",
        "tagline": "Test",
        "description": "Test description.",
        "portfolioHighlights": "not-an-array",  # should be array
    }
    data_dir = _write_data_dir(tmp_path, "about.json", bad_about)
    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("about.json")

    assert passed is False, "Expected type violation to be detected"
    assert len(errors) > 0
    assert any("portfolioHighlights" in err for err in errors), (
        f"Expected error to mention 'portfolioHighlights', got: {errors}"
    )


# ---------------------------------------------------------------------------
# (b) Missing required field → FAIL
# ---------------------------------------------------------------------------


def test_missing_required_field_fails(monkeypatch, tmp_path):
    """A skills file missing the required 'categories' key must be rejected."""
    bad_skills = {}  # 'categories' is required
    data_dir = _write_data_dir(tmp_path, "skills.json", bad_skills)
    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")

    assert passed is False, "Expected missing required field to be detected"
    assert len(errors) > 0


# ---------------------------------------------------------------------------
# (c) oneOf violation (object missing 'name') → FAIL
# ---------------------------------------------------------------------------


def test_oneof_violation_fails(monkeypatch, tmp_path):
    """A skill object missing 'name' satisfies neither oneOf branch → FAIL."""
    skills_data = {
        "categories": [
            {"label": "Backend", "details": [{"icon": "nestjs"}]}  # missing 'name'
        ]
    }
    data_dir = _write_data_dir(tmp_path, "skills.json", skills_data)
    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")

    assert passed is False, "Expected oneOf violation (object missing 'name') to be rejected"
    assert len(errors) > 0


# ---------------------------------------------------------------------------
# (d) Valid data → PASS
# ---------------------------------------------------------------------------


def test_valid_skills_passes(monkeypatch, tmp_path):
    """A fully valid skills file must pass jsonschema validation."""
    skills_data = {
        "categories": [
            {
                "label": "Backend",
                "details": [
                    "Python",
                    {"name": "NestJS", "icon": "nestjs"},
                ],
            }
        ]
    }
    data_dir = _write_data_dir(tmp_path, "skills.json", skills_data)
    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")

    assert passed is True, f"Expected valid skills to pass, got errors: {errors}"
    assert errors == []
