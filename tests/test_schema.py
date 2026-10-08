"""Schema validation tests — confirm about.schema.json is non-breaking."""

import importlib.resources
import json
from pathlib import Path

# Import the module under test
import profilekit.validate as validate
from tests.conftest import FIXTURES_DIR

# Schemas are packaged data (src/profilekit/schemas/), not a repo-relative
# path — resolve the same way the production code does.
SCHEMAS_DIR = importlib.resources.files("profilekit.schemas")


def _write_about_fixture(tmp_path: Path, data: dict) -> Path:
    """Write data as about.json inside a fresh tmp data dir and return the dir."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "about.json").write_text(json.dumps(data))
    return data_dir


def test_legacy_about_validates(monkeypatch, tmp_path):
    """about_minimal.json (no new fields) must validate cleanly."""
    minimal = json.loads((FIXTURES_DIR / "about_minimal.json").read_text())
    data_dir = _write_about_fixture(tmp_path, minimal)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("about.json")
    assert passed is True, f"Expected validation to pass but got errors: {errors}"
    assert errors == []


def test_typed_fields_validate(monkeypatch, tmp_path):
    """about_full.json (all five new fields present with correct types) must validate cleanly."""
    full = json.loads((FIXTURES_DIR / "about_full.json").read_text())
    data_dir = _write_about_fixture(tmp_path, full)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("about.json")
    assert passed is True, f"Expected validation to pass but got errors: {errors}"
    assert errors == []


def test_wrong_type_fails(monkeypatch, tmp_path):
    """portfolioHighlights set to a string (not array) must fail validation."""
    bad_data = {
        "username": "testuser",
        "tagline": "Test tagline",
        "description": "Test description.",
        "portfolioHighlights": "not-an-array",
    }
    data_dir = _write_about_fixture(tmp_path, bad_data)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("about.json")
    assert passed is False, "Expected validation to fail for wrong type"
    assert len(errors) > 0, "Expected at least one error message"
    assert any("portfolioHighlights" in err for err in errors), (
        f"Expected an error mentioning 'portfolioHighlights', got: {errors}"
    )


# Phase 3 — skills schema: widen details.items to oneOf[string, object]


def _write_skills_fixture(tmp_path: Path, data: dict) -> Path:
    """Write data as skills.json inside a fresh tmp data dir and return the dir."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "skills.json").write_text(json.dumps(data))
    return data_dir


def test_skills_object_entry_valid(monkeypatch, tmp_path):
    """A skills.json with an object entry {name, icon} must pass schema validation."""
    skills_data = {
        "categories": [{"label": "Backend", "details": [{"name": "NestJS", "icon": "nestjs"}]}]
    }
    data_dir = _write_skills_fixture(tmp_path, skills_data)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")
    assert passed is True, f"Expected validation to pass for object entry but got errors: {errors}"
    assert errors == []


def test_skills_string_entry_still_valid(monkeypatch, tmp_path):
    """A skills.json with all-string details must still pass schema validation (regression guard)."""
    skills_data = {"categories": [{"label": "Backend", "details": ["Python", "FastAPI"]}]}
    data_dir = _write_skills_fixture(tmp_path, skills_data)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")
    assert passed is True, f"Expected string entries to still be valid but got errors: {errors}"
    assert errors == []


def test_skills_object_missing_name_invalid(monkeypatch, tmp_path):
    """An object entry missing 'name' must be rejected by the jsonschema validator.

    The skills.schema.json enforces ``oneOf[string, object(required: name)]``.
    jsonschema.Draft7Validator enforces this natively — an object without
    ``name`` satisfies neither oneOf branch and therefore MUST fail validation.
    """
    skills_data = {"categories": [{"label": "Backend", "details": [{"icon": "nestjs"}]}]}
    data_dir = _write_skills_fixture(tmp_path, skills_data)

    monkeypatch.setattr(validate, "DATA_DIR", data_dir)
    monkeypatch.setattr(validate, "SCHEMAS_DIR", SCHEMAS_DIR)

    passed, errors = validate.validate_file("skills.json")
    assert passed is False, (
        "jsonschema enforces oneOf inside array items — an object missing 'name' "
        "satisfies neither branch and MUST be rejected."
    )
    assert len(errors) > 0, "Expected at least one validation error"
