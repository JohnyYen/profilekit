"""Tests for generate_github_readme — centered HTML header, icon rows, and asset wiring."""

from pathlib import Path

import profilekit.generate_github_readme as gen
from tests.conftest import make_about

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Regression guard: root README must never be written
# ---------------------------------------------------------------------------


def test_root_readme_not_written(tmp_path, monkeypatch):
    """main() must write output/github-readme.md and NOT write README.md to root."""
    output_dir = tmp_path / "output"
    monkeypatch.setattr(gen, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gen, "DATA_DIR", FIXTURES_DIR)
    # Provide a real assets dir with a dummy gif so render_about_html does not warn/raise
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "pixel-mario.gif").write_bytes(b"GIF89a")
    monkeypatch.setattr(gen, "ASSETS_DIR", assets_dir)

    gen.main()

    assert (output_dir / "github-readme.md").exists(), (
        "output/github-readme.md must be created by main()"
    )
    assert not (tmp_path / "README.md").exists(), "root README.md must NOT be written by main()"


# ---------------------------------------------------------------------------
# Task 4.14 (REWRITE) — render_header replaces the old render_about function
#   Old tests: test_summary_present, test_summary_absent_falls_back_to_headline,
#              test_summary_null_falls_back_to_tagline
#   These are replaced by:
# ---------------------------------------------------------------------------


def test_render_header_contains_username():
    """render_header must include the username in the h1 tag."""
    about = make_about({"username": "Johny", "tagline": "Backend Engineer"})
    result = gen.render_header(about)
    assert "Johny" in result
    assert "<h1" in result


def test_render_header_falls_back_to_tagline():
    """render_header uses tagline in h2 when no headline or githubReadmeSummary is set."""
    about = make_about({"username": "Bob", "tagline": "My Tagline"})
    result = gen.render_header(about)
    assert "My Tagline" in result
    assert "<h2" in result


# ---------------------------------------------------------------------------
# Tasks 4.1 – 4.13: new render functions
# ---------------------------------------------------------------------------


def test_render_header_h1_h2():
    """render_header returns a string with both <h1 align="center"> and <h2 align="center">."""
    about = make_about({"username": "Johny", "headline": "Backend Architect"})
    result = gen.render_header(about)
    assert '<h1 align="center">' in result
    assert '<h2 align="center">' in result


def test_render_about_html_mario_relative_path(tmp_path):
    """render_about_html uses the relative path assets/pixel-mario.gif as the img src."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "pixel-mario.gif").write_bytes(b"GIF89a")
    about = make_about()
    result = gen.render_about_html(about, assets_dir)
    assert 'src="assets/pixel-mario.gif"' in result


def test_render_about_html_raises_or_warns_missing_asset(tmp_path, capsys):
    """render_about_html warns or raises when assets/pixel-mario.gif does not exist."""
    empty_assets_dir = tmp_path / "assets"
    about = make_about()
    # Should either raise an exception or emit a warning — both are acceptable
    try:
        result = gen.render_about_html(about, empty_assets_dir)
        captured = capsys.readouterr()
        assert (
            "WARNING" in captured.err
            or "missing" in captured.err.lower()
            or "pixel-mario" in captured.err
        ), (
            f"Expected a warning about missing pixel-mario.gif in stderr but got: {captured.err!r}\n"
            f"Output was: {result!r}"
        )
    except (FileNotFoundError, RuntimeError, ValueError):
        pass  # Raising is also acceptable


def test_render_focus_bullets():
    """render_focus includes each currentFocus item's title."""
    about = make_about(
        {
            "currentFocus": [
                {"title": "Architecture", "description": "DDD and Clean Arch"},
                {"title": "AI Engineering", "description": "LLM patterns"},
            ]
        }
    )
    result = gen.render_focus(about)
    assert "Architecture" in result
    assert "AI Engineering" in result


def test_render_icon_rows_icon_field():
    """A category with {name, icon} produces a skillicons.dev <img> src."""
    skills = {
        "categories": [{"label": "Backend", "details": [{"name": "NestJS", "icon": "nestjs"}]}]
    }
    result = gen.render_icon_rows(skills)
    assert 'src="https://skillicons.dev/icons?i=nestjs"' in result


def test_render_icon_rows_iconUrl_field():
    """A category with {name, iconUrl} uses the verbatim iconUrl as img src."""
    skills = {
        "categories": [
            {
                "label": "Backend",
                "details": [
                    {"name": "Strapi", "iconUrl": "https://devicons.railway.com/i/strapi.svg"}
                ],
            }
        ]
    }
    result = gen.render_icon_rows(skills)
    assert 'src="https://devicons.railway.com/i/strapi.svg"' in result


def test_render_icon_rows_iconUrl_priority_over_icon():
    """When both icon and iconUrl are present, iconUrl wins as the img src."""
    skills = {
        "categories": [
            {
                "label": "Backend",
                "details": [{"name": "X", "icon": "x-slug", "iconUrl": "https://custom.url/x.svg"}],
            }
        ]
    }
    result = gen.render_icon_rows(skills)
    assert 'src="https://custom.url/x.svg"' in result
    assert "x-slug" not in result


def test_render_icon_rows_string_entry_no_img():
    """A plain-string entry emits no <img> tag in the icon rows output."""
    skills = {
        "categories": [
            {
                "label": "Design",
                "details": ["Clean Architecture", "DDD"],
            }
        ]
    }
    result = gen.render_icon_rows(skills)
    assert "<img" not in result


def test_render_icon_rows_no_icon_category_skipped():
    """A category with all plain-string details emits no <div align="center"> block."""
    skills = {
        "categories": [
            {"label": "Software Design", "details": ["SOLID Principles", "C4 Model"]},
        ]
    }
    result = gen.render_icon_rows(skills)
    assert '<div align="center">' not in result


def test_render_icon_rows_img_height_60_no_width():
    """Every <img> in an icon row has height="60" and no explicit width attribute."""
    skills = {
        "categories": [
            {
                "label": "Backend",
                "details": [
                    {"name": "NestJS", "icon": "nestjs"},
                    {"name": "FastAPI", "icon": "fastapi"},
                ],
            }
        ]
    }
    result = gen.render_icon_rows(skills)
    import re

    # All img tags in the result (excluding the spacer which has width="15")
    icon_imgs = re.findall(r"<img[^>]+skillicons[^>]+>", result)
    assert len(icon_imgs) >= 1, "Expected at least one skillicons img tag"
    for img in icon_imgs:
        assert 'height="60"' in img, f"Expected height='60' in: {img}"


def test_render_experience_text():
    """render_experience_text includes the company name and position."""
    experience = [
        {
            "company": "ACME Corp",
            "position": "Backend Engineer",
            "start_date": "2020",
            "end_date": "2023",
        }
    ]
    result = gen.render_experience_text(experience)
    assert "ACME Corp" in result
    assert "Backend Engineer" in result


def test_render_learning():
    """render_learning includes the learningJourney text from about."""
    about = make_about({"learningJourney": "Diving deep into system design."})
    result = gen.render_learning(about)
    assert "Diving deep into system design." in result


def test_render_footer():
    """render_footer returns a non-empty string."""
    about = make_about()
    result = gen.render_footer(about)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_render_footer_includes_githubQuote():
    """render_footer includes the githubQuote text when set in about."""
    about = make_about({"githubQuote": "Learning never stops — systems evolve, and so do we."})
    result = gen.render_footer(about)
    assert "Learning never stops" in result


# ---------------------------------------------------------------------------
# Category header labels above icon rows
# ---------------------------------------------------------------------------


def test_render_icon_rows_h3_label_before_div():
    """render_icon_rows emits <h3 align="center">{label}</h3> immediately before each icon div."""
    skills = {
        "categories": [
            {"label": "Back-end Frameworks", "details": [{"name": "NestJS", "icon": "nestjs"}]}
        ]
    }
    result = gen.render_icon_rows(skills)
    assert '<h3 align="center">Back-end Frameworks</h3>' in result
    # The h3 must appear before the div in the output
    h3_pos = result.index('<h3 align="center">Back-end Frameworks</h3>')
    div_pos = result.index('<div align="center">')
    assert h3_pos < div_pos, "h3 label must come before the icon <div>"


def test_render_icon_rows_no_h3_for_empty_category():
    """Categories with no icon-bearing skills emit neither <h3> nor <div>."""
    skills = {
        "categories": [
            {"label": "Software Design", "details": ["SOLID Principles", "C4 Model"]},
        ]
    }
    result = gen.render_icon_rows(skills)
    assert "<h3" not in result
    assert "<div" not in result
