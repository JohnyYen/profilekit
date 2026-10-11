"""Golden/snapshot tests — each generator's output must be byte-identical to
the committed reference snapshots under ``tests/golden/``.

Regeneration path:
    REGEN_GOLDEN=1 .venv/bin/python -m pytest tests/test_golden.py -v

When ``REGEN_GOLDEN=1`` is set, the test overwrites the golden file rather
than asserting equality. Use this after intentional output changes, then
commit the updated golden.
"""

import os
from pathlib import Path

from profilekit.context import ProjectContext

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
ROOT_DIR = Path(__file__).resolve().parent.parent


def _run_generator(generator_module, tmp_output_dir: Path) -> None:
    """Run *generator_module*.main() against the repository's real data.

    The context reads the repository's canonical ``data/`` and ``assets/`` so
    the snapshot reflects the published artifacts, but writes into a temporary
    directory so running the suite never mutates the committed ``output/``.
    """
    ctx = ProjectContext.for_root(ROOT_DIR, output_dir=tmp_output_dir)
    generator_module.main(ctx)


def _assert_or_regen(generated_path: Path, golden_path: Path) -> None:
    """Assert byte-equality or regenerate the golden file when REGEN_GOLDEN=1."""
    actual = generated_path.read_text(encoding="utf-8")
    if os.environ.get("REGEN_GOLDEN") == "1":
        golden_path.write_text(actual, encoding="utf-8")
        return
    expected = golden_path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Output does not match golden snapshot.\n"
        f"Golden: {golden_path}\n"
        f"Generated: {generated_path}\n"
        f"Run with REGEN_GOLDEN=1 to update the snapshot."
    )


# ---------------------------------------------------------------------------
# github-readme.md
# ---------------------------------------------------------------------------


def test_golden_github_readme(tmp_path):
    """github-readme.md must be byte-identical to tests/golden/github-readme.md."""
    import profilekit.generate_github_readme as gen

    _run_generator(gen, tmp_path)

    _assert_or_regen(tmp_path / "github-readme.md", GOLDEN_DIR / "github-readme.md")


# ---------------------------------------------------------------------------
# linkedin.md
# ---------------------------------------------------------------------------


def test_golden_linkedin(tmp_path):
    """linkedin.md must be byte-identical to tests/golden/linkedin.md."""
    import profilekit.generate_linkedin as gen

    _run_generator(gen, tmp_path)

    _assert_or_regen(tmp_path / "linkedin.md", GOLDEN_DIR / "linkedin.md")


# ---------------------------------------------------------------------------
# cv.md
# ---------------------------------------------------------------------------


def test_golden_cv_md(tmp_path):
    """cv.md must be byte-identical to tests/golden/cv.md."""
    import profilekit.generate_cv as gen

    _run_generator(gen, tmp_path)

    _assert_or_regen(tmp_path / "cv.md", GOLDEN_DIR / "cv.md")


# ---------------------------------------------------------------------------
# cv.yml
# ---------------------------------------------------------------------------


def test_golden_cv_yml(tmp_path):
    """cv.yml must be byte-identical to tests/golden/cv.yml."""
    import profilekit.generate_cv as gen

    _run_generator(gen, tmp_path)

    _assert_or_regen(tmp_path / "cv.yml", GOLDEN_DIR / "cv.yml")


# ---------------------------------------------------------------------------
# portfolio.md
# ---------------------------------------------------------------------------


def test_golden_portfolio(tmp_path):
    """portfolio.md must be byte-identical to tests/golden/portfolio.md."""
    import profilekit.generate_portfolio as gen

    _run_generator(gen, tmp_path)

    _assert_or_regen(tmp_path / "portfolio.md", GOLDEN_DIR / "portfolio.md")
