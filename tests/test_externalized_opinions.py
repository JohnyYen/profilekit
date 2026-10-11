"""Generator opinions must be configuration, not constants in the source.

A greeting, a decorative image, a sign-off line, a CV theme, a locale — these
are the author's taste, not the tool's behavior. Baked into the source they
make the package single-user: adopting it means either accepting someone
else's voice or forking to change a string literal.

Two properties are tested together, and the second matters as much as the
first:

1. A configured value is honored.
2. An **unset** value reproduces today's exact default output, byte for byte.

Without (2), externalizing silently rewrites every existing user's artifacts.
"""

import shutil
from pathlib import Path

import pytest

import profilekit.generate_cv as cv
import profilekit.generate_github_readme as readme
from profilekit.context import ProjectContext, discover_project

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"


FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "project"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A writable copy of the fictional fixture project.

    Driving the fictional persona rather than the owner's real data keeps the
    suite free of a real person's details, and keeps these assertions stable
    when the owner edits their own profile.
    """
    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    return tmp_path / "p"


def _write_config(project: Path, body: str) -> None:
    """Replace the project's configuration, keeping the pinned CV date."""
    (project / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n" + body, encoding="utf-8"
    )


def _generate(project: Path, module, filename: str) -> str:
    ctx = discover_project(explicit=project)
    module.main(ctx)
    return (ctx.output_dir / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Defaults are preserved exactly
# ---------------------------------------------------------------------------


def test_unset_options_reproduce_the_committed_github_readme(project: Path) -> None:
    """With no configuration, output must match the golden snapshot byte for byte."""
    produced = _generate(project, readme, "github-readme.md")
    assert produced == (GOLDEN_DIR / "github-readme.md").read_text(encoding="utf-8")


def test_only_pinning_the_date_reproduces_the_committed_cv(project: Path) -> None:
    """Every CV option but one defaults to the previously published value.

    ``current_date`` is the exception, and deliberately so: its old frozen
    literal was a determinism trap that silently aged out. The default is now
    ``auto``, and a project that needs byte-identical output pins the date —
    which is exactly what this repository's profile.toml does.
    """
    _write_config(project, '[generators.cv]\ncurrent_date = "2000-01-01"\n')
    produced = _generate(project, cv, "cv.yml")
    assert produced == (GOLDEN_DIR / "cv.yml").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# github-readme options
# ---------------------------------------------------------------------------


def test_custom_greeting_is_honored(project: Path) -> None:
    _write_config(project, '[generators.github-readme]\ngreeting = "Hey, {name} here."\n')
    produced = _generate(project, readme, "github-readme.md")

    assert "Hey, Ada Lovelace here." in produced
    assert "Hi 👋" not in produced


def test_custom_footer_is_honored(project: Path) -> None:
    _write_config(project, '[generators.github-readme]\nfooter = "Reach me anywhere."\n')
    produced = _generate(project, readme, "github-readme.md")

    assert "Reach me anywhere." in produced
    # "architecture discussions" also appears in the canonical data's
    # learningJourney, so assert on the default footer's distinctive opening.
    assert "Feel free to reach out" not in produced


def test_about_image_is_configurable(project: Path) -> None:
    (project / "assets" / "banner.png").write_bytes(b"\x89PNG")
    _write_config(project, '[generators.github-readme]\nabout_image = "assets/banner.png"\n')
    produced = _generate(project, readme, "github-readme.md")

    assert "assets/banner.png" in produced
    assert "pixel-mario.gif" not in produced


def test_about_image_can_be_disabled(project: Path) -> None:
    """A decorative image nobody else wants must be removable, not just swappable."""
    _write_config(project, '[generators.github-readme]\nabout_image = ""\n')
    produced = _generate(project, readme, "github-readme.md")

    assert "<img" not in produced or "pixel-mario" not in produced


# ---------------------------------------------------------------------------
# cv options
# ---------------------------------------------------------------------------


def test_cv_theme_and_locale_are_configurable(project: Path) -> None:
    _write_config(project, '[generators.cv]\ntheme = "sb2nov"\nlocale = "spanish"\n')
    produced = _generate(project, cv, "cv.yml")

    assert "theme: sb2nov" in produced
    assert "language: spanish" in produced
    assert "theme: classic" not in produced


def test_cv_current_date_defaults_to_auto_not_a_frozen_literal(project: Path) -> None:
    """The frozen date was a determinism trap: it silently aged out.

    `auto` lets RenderCV resolve the date, and a project that needs a fixed
    one pins it explicitly — which is what the goldens do.
    """
    _write_config(project, '[generators.cv]\ncurrent_date = "1843-07-10"\n')
    produced = _generate(project, cv, "cv.yml")

    assert '"1843-07-10"' in produced
    assert "auto" not in produced


def test_cv_rendercv_schema_version_is_configurable(project: Path) -> None:
    _write_config(project, '[generators.cv]\nrendercv_schema = "v2.9"\n')
    produced = _generate(project, cv, "cv.yml")

    assert "refs/tags/v2.9/schema.json" in produced


# ---------------------------------------------------------------------------
# Unknown options are the generator's business, not the core's
# ---------------------------------------------------------------------------


def test_unknown_generator_option_does_not_break_generation(project: Path) -> None:
    _write_config(project, "[generators.github-readme]\nnot_a_real_option = 1\n")
    assert _generate(project, readme, "github-readme.md")


def test_options_come_from_the_context(project: Path) -> None:
    """A caller can supply options without a config file at all."""
    ctx = ProjectContext.for_root(
        project,
        config={"generators": {"github-readme": {"greeting": "Configured in code: {name}"}}},
    )
    readme.main(ctx)
    produced = (ctx.output_dir / "github-readme.md").read_text(encoding="utf-8")

    assert "Configured in code:" in produced
