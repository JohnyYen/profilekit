"""This repository's own ``profile.toml`` must reproduce the legacy paths.

This repo is the tool's first consumer, so it is also the cutover guard. The
move from ``__file__``-derived constants to working-directory discovery is
only behavior-preserving if discovery resolves to exactly the same
directories. If it does not, the committed ``output/`` tree starts drifting
for reasons that have nothing to do with the data — and the freshness gate
would fail while pointing at the wrong cause.
"""

from pathlib import Path

from profilekit.context import CONFIG_FILENAME, discover_project

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_repository_declares_itself_a_project() -> None:
    assert (REPO_ROOT / CONFIG_FILENAME).is_file(), (
        f"the repository must ship a {CONFIG_FILENAME} so it can be discovered"
    )


def test_discovery_reproduces_the_legacy_paths() -> None:
    """The directories the old module-level constants pointed at, exactly."""
    ctx = discover_project(explicit=REPO_ROOT)

    assert ctx.root == REPO_ROOT
    assert ctx.data_dir == REPO_ROOT / "data"
    assert ctx.output_dir == REPO_ROOT / "output"
    assert ctx.assets_dir == REPO_ROOT / "assets"


def test_schemas_resolve_to_packaged_data_not_a_repo_directory() -> None:
    """Schemas ship inside the distribution, so the project must not override them.

    An installed CLI has no repository to read ``schemas/`` from; overriding
    this path here would hide that and make the package look functional while
    only working from a checkout.
    """
    assert discover_project(explicit=REPO_ROOT).schemas_dir is None


def test_portfolio_destination_is_declared_as_a_publisher() -> None:
    """The portfolio app data is published, never generated."""
    destinations = discover_project(explicit=REPO_ROOT).publisher_destinations()

    portfolio = destinations["portfolio-data"]
    assert portfolio["kind"] == "filesystem"
    assert portfolio["destination"] == "apps/portfolio/app/data"


def test_linkedin_destination_is_manual_by_capability() -> None:
    """LinkedIn has no write API for profile fields; the config must say so."""
    destinations = discover_project(explicit=REPO_ROOT).publisher_destinations()
    assert destinations["linkedin"]["kind"] == "manual"
