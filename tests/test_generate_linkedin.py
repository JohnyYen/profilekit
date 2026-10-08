"""Tests for generate_linkedin — cover linkedinHeadline wiring, 220-char cap, and full profile rendering."""

from pathlib import Path

import profilekit.generate_linkedin as gen
from tests.conftest import make_about

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_linkedin_headline_present_within_limit():
    """When linkedinHeadline is present and within 220 chars, it is returned as-is."""
    about = make_about({"linkedinHeadline": "Exact"})
    result = gen.compute_headline(about)
    assert result == "Exact", f"Expected 'Exact' but got {result!r}"


def test_linkedin_headline_exceeds_220(capsys):
    """When linkedinHeadline exceeds 220 chars, result is truncated to <=220 and stderr warns."""
    long_headline = "A" * 100 + " " + "B" * 100 + " " + "C" * 50
    about = make_about({"linkedinHeadline": long_headline})
    result = gen.compute_headline(about)

    assert len(result) <= 220, f"Expected result length <= 220 but got {len(result)}"
    captured = capsys.readouterr()
    assert (
        "220" in captured.err or "warning" in captured.err.lower() or "warn" in captured.err.lower()
    ), f"Expected a warning about the 220-char limit in stderr but got: {captured.err!r}"


def test_linkedin_headline_absent_falls_back():
    """When linkedinHeadline is absent, falls back to headline field."""
    about = make_about({"headline": "H"})
    # linkedinHeadline is NOT in the dict
    result = gen.compute_headline(about)
    assert result == "H", f"Expected 'H' (headline fallback) but got {result!r}"


# Phase 3 — Pure render function tests


def test_render_linkedin_about_has_about_section():
    """render_linkedin_about returns a string with '## About' and the about.description."""
    about = make_about({"description": "I am a backend engineer."})
    result = gen.render_linkedin_about(about)
    assert "## About" in result
    assert "I am a backend engineer." in result


def test_render_linkedin_about_includes_current_focus():
    """render_linkedin_about includes a Current Focus subsection when present."""
    about = make_about(
        {
            "description": "Test.",
            "currentFocus": [{"title": "Architecture", "description": "DDD patterns"}],
        }
    )
    result = gen.render_linkedin_about(about)
    assert "Current Focus" in result
    assert "Architecture" in result


def test_render_linkedin_experience_has_heading():
    """render_linkedin_experience returns a string with '## Experience'."""
    experience = [
        {"company": "ACME Corp", "position": "Engineer", "start_date": "2020", "end_date": "2023"}
    ]
    result = gen.render_linkedin_experience(experience)
    assert "## Experience" in result
    assert "ACME Corp" in result


def test_render_linkedin_experience_multiple_entries():
    """render_linkedin_experience includes all entries when multiple are given."""
    experience = [
        {"company": "First Inc", "position": "Dev", "start_date": "2018", "end_date": "2020"},
        {"company": "Second LLC", "position": "Lead", "start_date": "2020", "end_date": "2023"},
    ]
    result = gen.render_linkedin_experience(experience)
    assert "First Inc" in result
    assert "Second LLC" in result


def test_render_linkedin_education_has_heading():
    """render_linkedin_education returns a string with '## Education' and an institution name."""
    education = [
        {
            "institution": "MIT",
            "degree": "B.S.",
            "area": "CS",
            "start_date": "2015",
            "end_date": "2019",
        }
    ]
    result = gen.render_linkedin_education(education)
    assert "## Education" in result
    assert "MIT" in result


def test_render_linkedin_education_multiple_entries():
    """render_linkedin_education includes all institutions."""
    education = [
        {
            "institution": "Harvard",
            "degree": "M.S.",
            "area": "ML",
            "start_date": "2019",
            "end_date": "2021",
        },
        {
            "institution": "MIT",
            "degree": "B.S.",
            "area": "CS",
            "start_date": "2015",
            "end_date": "2019",
        },
    ]
    result = gen.render_linkedin_education(education)
    assert "Harvard" in result
    assert "MIT" in result


def test_render_linkedin_skills_has_heading():
    """render_linkedin_skills returns a string with '## Skills' and a category label."""
    skills = {"categories": [{"label": "Backend", "details": ["Python", "FastAPI"]}]}
    result = gen.render_linkedin_skills(skills)
    assert "## Skills" in result
    assert "Backend" in result


def test_render_linkedin_skills_includes_details():
    """render_linkedin_skills includes skill details for each category."""
    skills = {
        "categories": [
            {"label": "Backend", "details": ["Python", "FastAPI"]},
            {"label": "Frontend", "details": ["React"]},
        ]
    }
    result = gen.render_linkedin_skills(skills)
    assert "Python" in result
    assert "React" in result


def test_linkedin_full_assembly(monkeypatch, tmp_path):
    """main() writes output/linkedin.md with all six required sections in order."""
    output_dir = tmp_path / "output"
    monkeypatch.setattr(gen, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gen, "DATA_DIR", FIXTURES_DIR)

    gen.main()

    content = (output_dir / "linkedin.md").read_text(encoding="utf-8")
    sections = [
        "## Headline",
        "## About",
        "## Current Focus",
        "## Experience",
        "## Education",
        "## Skills",
    ]
    indices = []
    for section in sections:
        assert section in content, f"Section '{section}' missing from linkedin.md"
        indices.append(content.index(section))
    # Verify sections appear in declaration order
    assert indices == sorted(indices), (
        "Sections must appear in order: Headline, About, Current Focus, Experience, Education, Skills"
    )


def test_linkedin_headline_fallback_when_linkedinHeadline_absent():
    """When about has no linkedinHeadline, compute_headline uses headline or tagline."""
    about = make_about({"headline": "Fallback Headline"})
    # Explicitly ensure no linkedinHeadline key
    about.pop("linkedinHeadline", None)
    result = gen.compute_headline(about)
    assert result == "Fallback Headline", (
        f"Expected 'Fallback Headline' from headline fallback but got {result!r}"
    )


# Phase 2 — Backward-compat: object-entry skill details


def test_render_linkedin_skills_object_entries():
    """render_linkedin_skills handles object-style entries without raising and includes the names."""
    skills = {
        "categories": [{"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]}]
    }
    result = gen.render_linkedin_skills(skills)
    assert "Python" in result
    assert "FastAPI" in result


def test_render_linkedin_skills_byte_stable_after_migration():
    """Object entries with same names produce identical text output as plain string entries."""
    string_skills = {"categories": [{"label": "Backend", "details": ["Python", "FastAPI"]}]}
    object_skills = {
        "categories": [{"label": "Backend", "details": [{"name": "Python"}, {"name": "FastAPI"}]}]
    }
    assert gen.render_linkedin_skills(string_skills) == gen.render_linkedin_skills(object_skills)
