"""TDD tests for profilekit's generate_portfolio_data module.

RED phase: these tests are written before the implementation module exists.
They cover builder correctness, output path isolation, and main() integration.
"""

import json
import sys
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
    from profilekit.generate_portfolio_data import build_about

    result = build_about(about_input)
    expected_keys = {"username", "tagline", "description", "currentFocus", "whatIBuild", "learningJourney"}
    assert set(result.keys()) == expected_keys, (
        f"Expected keys {expected_keys!r}, got {set(result.keys())!r}"
    )


# ── Task 1.3.2 — build_about values match golden ──────────────────────────────

def test_build_about_values_match_golden(about_input, about_golden):
    """build_about(about_input) must match about_golden.json byte-for-byte."""
    from profilekit.generate_portfolio_data import build_about

    result = build_about(about_input)
    assert result == about_golden, (
        f"build_about output does not match golden.\nGot: {result!r}\nExpected: {about_golden!r}"
    )


# ── Task 1.3.3 — build_social passthrough ─────────────────────────────────────

def test_build_social_passthrough(social_input, social_golden):
    """build_social() must return input unchanged (full passthrough)."""
    from profilekit.generate_portfolio_data import build_social

    result = build_social(social_input)
    assert result == social_golden


# ── Task 1.3.4 — build_skills preserves categories ────────────────────────────

def test_build_skills_passthrough_preserves_categories(skills_input, skills_golden):
    """build_skills() must preserve all N categories in order, all M details per category."""
    from profilekit.generate_portfolio_data import build_skills

    result = build_skills(skills_input)
    assert result == skills_golden
    # Extra structural assertions
    categories_in = skills_input["categories"]
    categories_out = result["categories"]
    assert len(categories_out) == len(categories_in), "Category count must be preserved."
    for i, (cat_in, cat_out) in enumerate(zip(categories_in, categories_out)):
        assert cat_out["label"] == cat_in["label"], f"Category {i} label mismatch."
        assert len(cat_out["details"]) == len(cat_in["details"]), (
            f"Category {i} detail count mismatch."
        )


# ── Task 1.3.5 — build_projects maps to four fields ──────────────────────────

def test_build_projects_maps_to_four_fields(projects_input):
    """Each output entry must have exactly {name, description, tech, url}."""
    from profilekit.generate_portfolio_data import build_projects

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
    from profilekit.generate_portfolio_data import build_projects

    input_data = [{"name": "NoTechNoUrl", "description": "desc"}]
    result = build_projects(input_data)
    assert result[0]["tech"] == ""
    assert result[0]["url"] == ""


# ── Task 1.3.7 — build_projects preserves source order ───────────────────────

def test_build_projects_preserves_source_order(projects_input):
    """Output order must match input order."""
    from profilekit.generate_portfolio_data import build_projects

    result = build_projects(projects_input)
    for i, (inp, out) in enumerate(zip(projects_input, result)):
        assert out["name"] == inp["name"], (
            f"Order mismatch at index {i}: expected {inp['name']!r}, got {out['name']!r}"
        )


# ── Task 1.3.8 — main() writes four files to PORTFOLIO_DATA_DIR ───────────────

def test_main_writes_four_files_to_portfolio_data_dir(tmp_path, monkeypatch):
    """main() monkeypatched to write to tmp_path; asserts 4 JSON files with correct content."""
    import profilekit.generate_portfolio_data as gpd

    monkeypatch.setattr(gpd, "PORTFOLIO_DATA_DIR", tmp_path)

    gpd.main()

    expected_files = {"about.json", "social.json", "skills.json", "projects.json"}
    written = {f.name for f in tmp_path.iterdir() if f.suffix == ".json"}
    assert written == expected_files, f"Expected {expected_files!r}, got {written!r}"

    # Spot-check about.json content
    about = json.loads((tmp_path / "about.json").read_text(encoding="utf-8"))
    assert "username" in about
    assert set(about.keys()) == {"username", "tagline", "description", "currentFocus", "whatIBuild", "learningJourney"}


# ── Task 1.3.9 — main() exits nonzero on missing canonical file ───────────────

def test_main_exits_nonzero_on_missing_canonical_file(tmp_path, monkeypatch, capsys):
    """Removing a source file causes main() to exit with code 1 and write to stderr."""
    import shutil
    import profilekit.generate_portfolio_data as gpd

    # Copy canonical data to a temp data dir and remove one file
    fake_data_dir = tmp_path / "data"
    shutil.copytree(ROOT_DIR / "data", fake_data_dir)
    (fake_data_dir / "about.json").unlink()

    monkeypatch.setattr(gpd, "DATA_DIR", fake_data_dir)
    monkeypatch.setattr(gpd, "PORTFOLIO_DATA_DIR", tmp_path / "app_data")

    with pytest.raises(SystemExit) as exc_info:
        gpd.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip(), "Expected a descriptive stderr message on missing file."


# ── Task 1.3.10 — threat boundary: no writes outside PORTFOLIO_DATA_DIR ───────

def test_generator_writes_only_to_portfolio_data_dir(tmp_path, monkeypatch):
    """main() must not write any file outside PORTFOLIO_DATA_DIR during execution."""
    import profilekit.generate_portfolio_data as gpd

    app_data_dir = tmp_path / "app_data"
    monkeypatch.setattr(gpd, "PORTFOLIO_DATA_DIR", app_data_dir)

    written_paths: list[Path] = []
    original_write_output = gpd.write_output

    def spy_write_output(content: str, output_dir: Path, filename: str) -> Path:
        path = original_write_output(content, output_dir, filename)
        written_paths.append(path.resolve())
        return path

    monkeypatch.setattr(gpd, "write_output", spy_write_output)
    gpd.main()

    app_data_resolved = app_data_dir.resolve()
    for written in written_paths:
        assert written.is_relative_to(app_data_resolved), (
            f"File written outside PORTFOLIO_DATA_DIR: {written}"
        )
