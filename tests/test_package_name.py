"""Non-colliding top-level package name (spec `package-distribution`, Req:
Non-colliding top-level package name).

The distributed package must not ship a top-level module named `generators`
(too generic, collides with the retired internal name) and must be
importable under its new, project-specific name: `profilekit`.
"""

import importlib.metadata
import importlib.util
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_profilekit_is_importable():
    spec = importlib.util.find_spec("profilekit")
    assert spec is not None, "the installed package must expose a 'profilekit' module"


def test_the_built_distribution_ships_only_profilekit_at_top_level():
    """Ask the build what it shipped, not the import system what it can find.

    ``find_spec("generators")`` answered a different question: whether
    *anything* importable by that name exists in this environment. A stale,
    untracked ``generators/__pycache__`` left over in an old checkout is an
    implicit namespace package, so that probe failed on a clean build and
    would pass on a dirty one for the wrong reason.

    ``top_level.txt`` is written by the setuptools build from the packages it
    actually discovered, so it is the shipped top-level set, for an editable
    install and a wheel alike.
    """
    distribution = importlib.metadata.distribution("profilekit")
    top_level = distribution.read_text("top_level.txt")
    assert top_level is not None, "the setuptools build must record its top-level packages"
    assert set(top_level.split()) == {"profilekit"}

    # A regular (non-editable) install also lists every shipped file.
    shipped_roots = {
        file.parts[0]
        for file in distribution.files or []
        if file.suffix == ".py" and not file.parts[0].startswith("..")
    }
    assert "generators" not in shipped_roots


def test_package_discovery_is_confined_to_the_profilekit_tree():
    """The build configuration, not the local tree, decides what ships.

    Discovery rooted at ``src/`` with no explicit package list cannot pick up
    a top-level ``generators`` directory at the repository root, whatever is
    lying around in a given checkout.
    """
    setuptools_config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["setuptools"]

    assert "packages" in setuptools_config, "package discovery must be configured explicitly"
    packages = setuptools_config["packages"]
    assert isinstance(packages, dict), "an explicit package list bypasses discovery"
    assert packages["find"]["where"] == ["src"]

    include = packages["find"].get("include", [])
    assert not any(pattern.split(".")[0] == "generators" for pattern in include)
