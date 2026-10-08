"""Tests for validate_portfolio_highlights — non-fatal validation against projects.json."""

import profilekit.validate as validate
from tests.conftest import make_about, make_projects


def test_all_highlights_valid(capsys):
    """When all portfolioHighlights names match projects, no warnings are emitted."""
    about = make_about({"portfolioHighlights": ["Alpha", "Beta"]})
    projects = make_projects(["Alpha", "Beta", "Gamma"])

    warnings = validate.validate_portfolio_highlights(about, projects)

    assert warnings == [], f"Expected no warnings but got: {warnings}"
    captured = capsys.readouterr()
    assert captured.err == "", f"Expected no stderr output but got: {captured.err!r}"


def test_highlight_unmatched_warns():
    """When a highlight name has no matching project, a warning is returned containing the name."""
    about = make_about({"portfolioHighlights": ["Alpha", "Missing-Project"]})
    projects = make_projects(["Alpha", "Beta"])

    warnings = validate.validate_portfolio_highlights(about, projects)

    assert len(warnings) >= 1, f"Expected at least one warning but got: {warnings}"
    assert any("Missing-Project" in w for w in warnings), (
        f"Expected a warning mentioning 'Missing-Project' but got: {warnings}"
    )


def test_highlights_over_6_warns():
    """When portfolioHighlights has 7+ entries, a warning about exceeding the 6-item limit is returned."""
    names = [f"Project{i}" for i in range(7)]
    about = make_about({"portfolioHighlights": names})
    projects = make_projects(names)

    warnings = validate.validate_portfolio_highlights(about, projects)

    assert any("6" in w for w in warnings), (
        f"Expected a warning mentioning the 6-item limit but got: {warnings}"
    )


def test_highlights_null_ok(capsys):
    """When portfolioHighlights is null (or absent), no warnings are emitted."""
    about = make_about({"portfolioHighlights": None})
    projects = make_projects(["Alpha", "Beta"])

    warnings = validate.validate_portfolio_highlights(about, projects)

    assert warnings == [], f"Expected no warnings for null portfolioHighlights but got: {warnings}"
    captured = capsys.readouterr()
    assert captured.err == "", f"Expected no stderr output but got: {captured.err!r}"
