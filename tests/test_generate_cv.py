"""Tests for generate_cv — cover cvHeadline wiring, render_cv_markdown, and dual output."""

from pathlib import Path

import profilekit.generate_cv as gen
from profilekit.context import ProjectContext
from tests.conftest import make_about

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_cv_headline_present():
    """When cvHeadline is set, compute_cv_headline returns the YAML-escaped cvHeadline."""
    about = make_about({"cvHeadline": "Arch Lead"})
    result = gen.compute_cv_headline(about)
    expected = gen.escape_yaml_string("Arch Lead")
    assert result == expected, (
        f"Expected escape_yaml_string('Arch Lead') = {expected!r} but got {result!r}"
    )


def test_cv_headline_absent_falls_back():
    """When cvHeadline is absent, compute_cv_headline falls back to headline."""
    about = make_about({"headline": "H"})
    # cvHeadline is NOT in the dict
    result = gen.compute_cv_headline(about)
    expected = gen.escape_yaml_string("H")
    assert result == expected, f"Expected escape_yaml_string('H') = {expected!r} but got {result!r}"


def test_cv_headline_null_falls_back_to_tagline():
    """When cvHeadline is null and headline is absent, tagline is used."""
    about = make_about({"cvHeadline": None})
    result = gen.compute_cv_headline(about)
    expected = gen.escape_yaml_string(about["tagline"])
    assert result == expected, f"Expected tagline fallback {expected!r} but got {result!r}"


# Phase 5 — render_cv_markdown tests


def _sample_experience() -> list:
    return [
        {
            "company": "Test Corp",
            "position": "Engineer",
            "start_date": "2020",
            "end_date": "2023",
            "highlights": ["Built APIs"],
        }
    ]


def _sample_education() -> list:
    return [
        {
            "institution": "Test Univ",
            "degree": "B.S.",
            "area": "CS",
            "start_date": "2016",
            "end_date": "2020",
        }
    ]


def _sample_skills() -> dict:
    return {"categories": [{"label": "Backend", "details": ["Python", "FastAPI"]}]}


def test_render_cv_markdown_has_headline_section():
    """render_cv_markdown output contains a headline string from about."""
    about = make_about({"headline": "Software Architect"})
    result = gen.render_cv_markdown(about, [], [], [], {}, {})
    assert "Software Architect" in result


def test_render_cv_markdown_has_experience_section():
    """render_cv_markdown output contains '## Experience' and at least one company name."""
    about = make_about()
    result = gen.render_cv_markdown(about, _sample_experience(), [], [], {}, {})
    assert "## Experience" in result
    assert "Test Corp" in result


def test_render_cv_markdown_has_education_section():
    """render_cv_markdown output contains '## Education' and at least one institution."""
    about = make_about()
    result = gen.render_cv_markdown(about, [], _sample_education(), [], {}, {})
    assert "## Education" in result
    assert "Test Univ" in result


def test_render_cv_markdown_has_skills_section():
    """render_cv_markdown output contains '## Skills' and at least one category label."""
    about = make_about()
    result = gen.render_cv_markdown(about, [], [], [], _sample_skills(), {})
    assert "## Skills" in result
    assert "Backend" in result


def test_cv_main_writes_cv_yml_to_output(monkeypatch, tmp_path):
    """main() writes output/cv.yml when OUTPUT_DIR and DATA_DIR are monkeypatched."""
    output_dir = tmp_path / "output"
    ctx = ProjectContext.for_root(tmp_path, data_dir=FIXTURES_DIR, output_dir=output_dir)
    gen.main(ctx)
    assert (output_dir / "cv.yml").exists(), "output/cv.yml must be written by main()"


def test_cv_main_writes_cv_md_to_output(monkeypatch, tmp_path):
    """main() writes output/cv.md when OUTPUT_DIR and DATA_DIR are monkeypatched."""
    output_dir = tmp_path / "output"
    ctx = ProjectContext.for_root(tmp_path, data_dir=FIXTURES_DIR, output_dir=output_dir)
    gen.main(ctx)
    assert (output_dir / "cv.md").exists(), "output/cv.md must be written by main()"


def test_cv_main_does_not_write_root_cv_yml(monkeypatch, tmp_path):
    """main() must NOT write cv.yml to the root (tmp_path stands in for ROOT_DIR)."""
    output_dir = tmp_path / "output"
    ctx = ProjectContext.for_root(tmp_path, data_dir=FIXTURES_DIR, output_dir=output_dir)
    gen.main(ctx)
    assert not (tmp_path / "cv.yml").exists(), (
        "root cv.yml must NOT be written; all CV output must go to output/"
    )


# Phase 2 — Backward-compat: object-entry skill details


def test_format_skill_entry_object_entries():
    """format_skill_entry handles object-style details without raising and includes the names."""
    cat = {"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]}
    result = gen.format_skill_entry(cat)
    assert "Python" in result
    assert "FastAPI" in result


def test_render_cv_markdown_skills_byte_stable_after_migration():
    """CV markdown skills section produces identical text for string and object entries."""
    string_skills = {"categories": [{"label": "Backend", "details": ["Python", "FastAPI"]}]}
    object_skills = {
        "categories": [{"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]}]
    }
    about = make_about()
    result_str = gen.render_cv_markdown(about, [], [], [], string_skills, {})
    result_obj = gen.render_cv_markdown(about, [], [], [], object_skills, {})

    # Extract just the skills section for comparison
    def extract_skills_section(text: str) -> str:
        lines = text.splitlines()
        in_skills = False
        result = []
        for line in lines:
            if line == "## Skills":
                in_skills = True
            if in_skills:
                result.append(line)
        return "\n".join(result)

    assert extract_skills_section(result_str) == extract_skills_section(result_obj)
