"""Tests for generators/utils.py — load_json, write_output, and skill normalization utilities."""

from generators.utils import skill_icon, skill_name, write_output


def test_write_output_creates_dir_and_file(tmp_path):
    """write_output creates the output directory and writes the file when dir is absent."""
    output_dir = tmp_path / "out"
    result = write_output("hello", output_dir, "x.md")
    assert output_dir.exists(), "output_dir must be created"
    assert (output_dir / "x.md").exists(), "target file must exist"
    assert (output_dir / "x.md").read_text(encoding="utf-8") == "hello"
    assert result == output_dir / "x.md"


def test_write_output_overwrites_existing_file(tmp_path):
    """write_output overwrites an existing file without raising an error."""
    output_dir = tmp_path / "out"
    write_output("first", output_dir, "x.md")
    write_output("second", output_dir, "x.md")
    assert (output_dir / "x.md").read_text(encoding="utf-8") == "second"


# Phase 1 — skill_name / skill_icon helpers


def test_skill_name_string():
    """skill_name on a plain string returns the string itself."""
    assert skill_name("Python") == "Python"


def test_skill_name_object():
    """skill_name on an object dict returns the 'name' value."""
    assert skill_name({"name": "NestJS", "icon": "nestjs"}) == "NestJS"


def test_skill_icon_string_returns_none():
    """skill_icon on a plain string returns None (no icon available for plain strings)."""
    assert skill_icon("Python") is None


def test_skill_icon_object_with_icon():
    """skill_icon on an object with 'icon' returns (slug, None)."""
    assert skill_icon({"name": "NestJS", "icon": "nestjs"}) == ("nestjs", None)


def test_skill_icon_object_with_iconUrl():
    """skill_icon on an object with 'iconUrl' returns (None, url)."""
    assert skill_icon(
        {"name": "Strapi", "iconUrl": "https://devicons.railway.com/i/strapi.svg"}
    ) == (
        None,
        "https://devicons.railway.com/i/strapi.svg",
    )


def test_skill_icon_object_with_both_prefers_iconUrl():
    """When both 'icon' and 'iconUrl' are present, iconUrl wins — (None, url)."""
    assert skill_icon({"name": "X", "icon": "x", "iconUrl": "https://u"}) == (None, "https://u")


def test_skill_icon_object_no_icon_fields():
    """skill_icon on an object with no icon fields returns (None, None)."""
    assert skill_icon({"name": "Docker"}) == (None, None)
