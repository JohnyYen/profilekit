"""Tests for generate_portfolio — compute_portfolio_projects and render_portfolio."""

from pathlib import Path

from profilekit.generate_portfolio import compute_portfolio_projects, render_portfolio
from tests.conftest import make_about, make_projects

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ── compute_portfolio_projects ────────────────────────────────────────────────


def test_compute_portfolio_projects_null_highlights_returns_all():
    """highlights=None → all projects returned in source order."""
    projects = make_projects(["A", "B", "C"])
    result = compute_portfolio_projects(projects, None)
    assert [p["name"] for p in result] == ["A", "B", "C"]


def test_compute_portfolio_projects_absent_highlights_returns_all():
    """highlights=[] (empty list, simulating absent field) → all projects returned."""
    projects = make_projects(["X", "Y"])
    result = compute_portfolio_projects(projects, [])
    assert [p["name"] for p in result] == ["X", "Y"]


def test_compute_portfolio_projects_filters_and_orders():
    """highlights=['C','A'], projects=[A,B,C] → returns [C,A] in highlight order."""
    projects = make_projects(["A", "B", "C"])
    result = compute_portfolio_projects(projects, ["C", "A"])
    assert [p["name"] for p in result] == ["C", "A"]


def test_compute_portfolio_projects_unmatched_skipped_and_warns(capsys):
    """highlights=['X','A'], projects=[A] → returns [A], stderr mentions 'X'."""
    projects = make_projects(["A"])
    result = compute_portfolio_projects(projects, ["X", "A"])
    assert [p["name"] for p in result] == ["A"]
    captured = capsys.readouterr()
    assert "X" in captured.err, f"Expected 'X' in stderr but got: {captured.err!r}"


def test_compute_portfolio_projects_all_unmatched(capsys):
    """All highlights unmatched → returns [], warns for each unmatched name."""
    projects = make_projects(["A", "B"])
    result = compute_portfolio_projects(projects, ["X", "Y"])
    assert result == []
    captured = capsys.readouterr()
    assert "X" in captured.err
    assert "Y" in captured.err


def test_compute_portfolio_projects_is_pure():
    """compute_portfolio_projects performs no file I/O — returns a list without side effects."""
    projects = make_projects(["Alpha", "Beta"])
    result = compute_portfolio_projects(projects, ["Alpha"])
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Alpha"


# ── render_portfolio ──────────────────────────────────────────────────────────


def _full_project() -> dict:
    return {
        "name": "My Project",
        "description": "A great project.",
        "tech": "Python, FastAPI",
        "url": "https://github.com/testuser/my-project",
        "highlights": ["Fast performance", "Clean code"],
    }


def test_render_portfolio_includes_name_description_tech():
    """A project with name/description/tech has all three present in output."""
    about = make_about()
    result = render_portfolio(about, [_full_project()])
    assert "My Project" in result
    assert "A great project." in result
    assert "Python, FastAPI" in result


def test_render_portfolio_url_renders_as_link():
    """A non-empty url is rendered as a markdown hyperlink."""
    about = make_about()
    result = render_portfolio(about, [_full_project()])
    assert "https://github.com/testuser/my-project" in result
    assert "[" in result
    assert "](" in result


def test_render_portfolio_empty_url_no_broken_link():
    """A project with url='' produces no empty parentheses link."""
    project = _full_project()
    project["url"] = ""
    about = make_about()
    result = render_portfolio(about, [project])
    assert "()" not in result, "Empty url must not produce a broken '()' link"


def test_render_portfolio_highlights_rendered_as_list():
    """Project highlights are rendered as '- item' list entries."""
    about = make_about()
    result = render_portfolio(about, [_full_project()])
    assert "- Fast performance" in result
    assert "- Clean code" in result


def test_render_portfolio_is_pure():
    """render_portfolio returns a non-empty string without writing any files."""
    about = make_about({"description": "My portfolio."})
    result = render_portfolio(about, [_full_project()])
    assert isinstance(result, str)
    assert len(result) > 0
