"""Tests for generators/render.py — shared pure formatting helpers.

All tests must fail before render.py exists.
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPERIENCE_ENTRY = {
    "company": "Test Corp",
    "position": "Engineer",
    "start_date": "2020",
    "end_date": "2023",
    "location": "Remote",
    "summary": "Built things.",
    "highlights": ["Shipped feature A"],
}

EDUCATION_ENTRY = {
    "institution": "Tech University",
    "area": "Computer Science",
    "degree": "BSc",
    "start_date": "2016",
    "end_date": "2020",
    "location": "City",
    "summary": "Graduated with honors.",
    "highlights": ["Dean's list"],
}


# ---------------------------------------------------------------------------
# (a) format_date_range
# ---------------------------------------------------------------------------

def test_format_date_range_with_end():
    """format_date_range returns 'start – end' when end is provided."""
    from generators.render import format_date_range

    result = format_date_range("2020", "2023")
    assert result == "2020 – 2023"


def test_format_date_range_defaults_end_to_present():
    """format_date_range returns 'start – Present' when end is empty."""
    from generators.render import format_date_range

    result = format_date_range("2020", "")
    assert result == "2020 – Present"


def test_format_date_range_custom_default():
    """format_date_range accepts a custom default_end value."""
    from generators.render import format_date_range

    result = format_date_range("2020", "", default_end="present")
    assert result == "2020 – present"


# ---------------------------------------------------------------------------
# (b) format_experience_entry_yaml
# ---------------------------------------------------------------------------

def test_format_experience_entry_yaml_contains_company():
    """format_experience_entry_yaml output contains the company name."""
    from generators.render import format_experience_entry_yaml

    result = format_experience_entry_yaml(EXPERIENCE_ENTRY)
    assert "Test Corp" in result


def test_format_experience_entry_yaml_contains_position():
    """format_experience_entry_yaml output contains the position."""
    from generators.render import format_experience_entry_yaml

    result = format_experience_entry_yaml(EXPERIENCE_ENTRY)
    assert "Engineer" in result


def test_format_experience_entry_yaml_contains_highlight():
    """format_experience_entry_yaml output includes highlights."""
    from generators.render import format_experience_entry_yaml

    result = format_experience_entry_yaml(EXPERIENCE_ENTRY)
    assert "Shipped feature A" in result


# ---------------------------------------------------------------------------
# (c) format_education_entry_yaml
# ---------------------------------------------------------------------------

def test_format_education_entry_yaml_contains_institution():
    """format_education_entry_yaml output contains the institution name."""
    from generators.render import format_education_entry_yaml

    result = format_education_entry_yaml(EDUCATION_ENTRY)
    assert "Tech University" in result


def test_format_education_entry_yaml_contains_degree():
    """format_education_entry_yaml output contains the degree."""
    from generators.render import format_education_entry_yaml

    result = format_education_entry_yaml(EDUCATION_ENTRY)
    assert "BSc" in result


# ---------------------------------------------------------------------------
# (d) format_experience_entry_md — markdown variant (linkedin/github)
# ---------------------------------------------------------------------------

def test_format_experience_entry_md_contains_company_and_position():
    """format_experience_entry_md produces a markdown block with company and position."""
    from generators.render import format_experience_entry_md

    result = format_experience_entry_md(EXPERIENCE_ENTRY)
    assert "Test Corp" in result
    assert "Engineer" in result


def test_format_experience_entry_md_contains_date_range():
    """format_experience_entry_md includes the formatted date range."""
    from generators.render import format_experience_entry_md

    result = format_experience_entry_md(EXPERIENCE_ENTRY)
    assert "2020" in result
    assert "2023" in result


def test_format_education_entry_md_contains_institution():
    """format_education_entry_md produces a markdown block with the institution."""
    from generators.render import format_education_entry_md

    result = format_education_entry_md(EDUCATION_ENTRY)
    assert "Tech University" in result
    assert "BSc" in result
