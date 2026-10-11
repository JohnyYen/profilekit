"""Transform correctness for the filesystem publisher.

These cover the pure data shaping — canonical JSON in, frontend JSON out.
The publisher's path safety, planning, idempotency, and write behavior live
in tests/test_publisher_filesystem.py.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_data"
ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_fixture(name: str):
    """Load a JSON fixture from tests/fixtures/portfolio_data/."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def about_input():
    return _load_fixture("about_input.json")


@pytest.fixture
def about_golden():
    return _load_fixture("about_golden.json")


@pytest.fixture
def social_input():
    return _load_fixture("social_input.json")


@pytest.fixture
def social_golden():
    return _load_fixture("social_golden.json")


@pytest.fixture
def skills_input():
    return _load_fixture("skills_input.json")


@pytest.fixture
def skills_golden():
    return _load_fixture("skills_golden.json")


@pytest.fixture
def projects_input():
    return _load_fixture("projects_input.json")


@pytest.fixture
def projects_golden():
    return _load_fixture("projects_golden.json")


# ── Task 1.3.1 — build_about returns 6-key subset ─────────────────────────────


def test_build_about_returns_six_key_subset(about_input):
    """build_about() output must have exactly the 6 expected keys; no extras."""
    from profilekit.publishers.filesystem import build_about

    result = build_about(about_input)
    expected_keys = {
        "username",
        "tagline",
        "description",
        "currentFocus",
        "whatIBuild",
        "learningJourney",
    }
    assert set(result.keys()) == expected_keys, (
        f"Expected keys {expected_keys!r}, got {set(result.keys())!r}"
    )


# ── Task 1.3.2 — build_about values match golden ──────────────────────────────


def test_build_about_values_match_golden(about_input, about_golden):
    """build_about(about_input) must match about_golden.json byte-for-byte."""
    from profilekit.publishers.filesystem import build_about

    result = build_about(about_input)
    assert result == about_golden, (
        f"build_about output does not match golden.\nGot: {result!r}\nExpected: {about_golden!r}"
    )


# ── Task 1.3.3 — build_social passthrough ─────────────────────────────────────


def test_build_social_passthrough(social_input, social_golden):
    """build_social() must return input unchanged (full passthrough)."""
    from profilekit.publishers.filesystem import build_social

    result = build_social(social_input)
    assert result == social_golden


# ── Task 1.3.4 — build_skills preserves categories ────────────────────────────


def test_build_skills_passthrough_preserves_categories(skills_input, skills_golden):
    """build_skills() must preserve all N categories in order, all M details per category."""
    from profilekit.publishers.filesystem import build_skills

    result = build_skills(skills_input)
    assert result == skills_golden
    # Extra structural assertions
    categories_in = skills_input["categories"]
    categories_out = result["categories"]
    assert len(categories_out) == len(categories_in), "Category count must be preserved."
    for i, (cat_in, cat_out) in enumerate(zip(categories_in, categories_out, strict=True)):
        assert cat_out["label"] == cat_in["label"], f"Category {i} label mismatch."
        assert len(cat_out["details"]) == len(cat_in["details"]), (
            f"Category {i} detail count mismatch."
        )


# ── Task 1.3.5 — build_projects maps to four fields ──────────────────────────


def test_build_projects_maps_to_four_fields(projects_input):
    """Each output entry must have exactly {name, description, tech, url}."""
    from profilekit.publishers.filesystem import build_projects

    result = build_projects(projects_input)
    assert isinstance(result, list)
    assert len(result) == len(projects_input)
    for entry in result:
        assert set(entry.keys()) == {"name", "description", "tech", "url"}, (
            f"Expected exactly 4 fields, got {set(entry.keys())!r}"
        )
        # Confirm canonical-only fields are absent
        for forbidden in ("start_date", "end_date", "highlights"):
            assert forbidden not in entry


# ── Task 1.3.6 — build_projects defaults missing tech/url to "" ───────────────


def test_build_projects_defaults_missing_tech_and_url_to_empty_string():
    """An input entry without 'tech' or 'url' must produce tech="" and url=""."""
    from profilekit.publishers.filesystem import build_projects

    input_data = [{"name": "NoTechNoUrl", "description": "desc"}]
    result = build_projects(input_data)
    assert result[0]["tech"] == ""
    assert result[0]["url"] == ""


# ── Task 1.3.7 — build_projects preserves source order ───────────────────────


def test_build_projects_preserves_source_order(projects_input):
    """Output order must match input order."""
    from profilekit.publishers.filesystem import build_projects

    result = build_projects(projects_input)
    for i, (inp, out) in enumerate(zip(projects_input, result, strict=True)):
        assert out["name"] == inp["name"], (
            f"Order mismatch at index {i}: expected {inp['name']!r}, got {out['name']!r}"
        )


# ── A missing canonical file must fail loudly, not publish a partial set ──────


def test_build_artifacts_exits_nonzero_on_missing_canonical_file(tmp_path):
    """Dropping one canonical file must abort before any artifact is produced."""
    import shutil

    from profilekit.context import ProjectContext
    from profilekit.publishers.filesystem import build_artifacts

    data_dir = tmp_path / "data"
    shutil.copytree(ROOT_DIR / "data", data_dir)
    (data_dir / "about.json").unlink()

    ctx = ProjectContext.for_root(tmp_path, data_dir=data_dir)
    with pytest.raises(SystemExit) as exc_info:
        build_artifacts(ctx)

    assert exc_info.value.code == 1
