"""Structural invariants of the consolidated monorepo (restructure-to-monorepo).

These guard the spec `monorepo-structure`: canonical layout, in-repo portfolio
and CV sources, the portfolio data carve-out, and the absence of submodules or
absorbed platform-forced targets.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL_DIRS = [
    "data",
    "src/profilekit",
    "output",
    "apps/portfolio",
    "cv",
    "tests",
]


def test_canonical_layout_present():
    # spec Req: Canonical repository layout
    missing = [d for d in CANONICAL_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"missing canonical directories: {missing}"


def test_portfolio_moved_in_repo():
    # spec Req: Portfolio moved in-repo and builds
    portfolio = ROOT / "apps" / "portfolio"
    assert (portfolio / "package.json").is_file()
    assert (portfolio / "pnpm-lock.yaml").is_file()


def test_portfolio_data_source_unchanged():
    # spec Req: Single source of truth — portfolio carve-out (deferred divergence)
    app_data = ROOT / "apps" / "portfolio" / "app" / "data"
    assert app_data.is_dir(), "portfolio app/data/ must remain after the move"
    assert any(app_data.iterdir()), "portfolio app/data/ must be non-empty"


def test_cv_config_present_without_divergent_json():
    # spec Req: In-repo CV config resolves data locally
    cv = ROOT / "cv"
    assert cv.is_dir()
    assert any(cv.iterdir()), "cv/ must contain the RenderCV configuration"
    # CV data is derived from output/cv.yml, not a hand-authored data/*.json copy.
    assert not (cv / "data").exists(), "cv/ must not hold a divergent data/ copy"


def test_no_submodules():
    # spec Req: Portfolio moved in-repo and builds — submodule check
    assert not (ROOT / ".gitmodules").exists()


# Removed: `test_github_profile_repo_not_absorbed` asserted that no directory
# literally named after the maintainer's GitHub handle existed at the root. That
# encoded one person's repository layout as a project invariant, which is
# meaningless for anyone else who adopts the package.
