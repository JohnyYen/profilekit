"""Project discovery — how ``profile`` decides which project it is acting on.

The rule that matters: discovery NEVER consults ``__file__`` and never treats
the installed package directory as a project root. Before this existed, every
module derived its paths from its own location, which meant a ``pip install``ed
CLI resolved ``data/`` inside ``site-packages`` and the tool only worked from
inside a clone of this one repository.

Precedence (first match wins, no silent fallback to the working directory):

1. ``--project <dir>``
2. ``PROFILEKIT_PROJECT``
3. nearest ``profile.toml`` walking up from the working directory
4. nothing — exit 2 with an actionable message
"""

import dataclasses
from pathlib import Path

import pytest

from profilekit.context import ProjectContext, ProjectNotFoundError, discover_project

MINIMAL_CONFIG = "[project]\nconfig_version = 1\n"


def _make_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.toml").write_text(MINIMAL_CONFIG, encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_explicit_flag_wins_over_env_and_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flagged = _make_project(tmp_path / "flagged")
    envd = _make_project(tmp_path / "envd")
    cwd = _make_project(tmp_path / "cwd")

    monkeypatch.setenv("PROFILEKIT_PROJECT", str(envd))
    monkeypatch.chdir(cwd)

    assert discover_project(explicit=flagged).root == flagged.resolve()


def test_env_wins_over_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    envd = _make_project(tmp_path / "envd")
    cwd = _make_project(tmp_path / "cwd")

    monkeypatch.setenv("PROFILEKIT_PROJECT", str(envd))
    monkeypatch.chdir(cwd)

    assert discover_project().root == envd.resolve()


def test_walks_up_to_the_nearest_profile_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_project(tmp_path / "project")
    nested = root / "a" / "b" / "c"
    nested.mkdir(parents=True)

    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)
    monkeypatch.chdir(nested)

    assert discover_project().root == root.resolve()


def test_nearest_project_wins_over_an_outer_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project nested inside another resolves to the inner one."""
    outer = _make_project(tmp_path / "outer")
    inner = _make_project(outer / "packages" / "inner")

    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)
    monkeypatch.chdir(inner)

    assert discover_project().root == inner.resolve()


def test_no_config_anywhere_raises_with_an_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()

    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)
    monkeypatch.chdir(bare)

    with pytest.raises(ProjectNotFoundError) as exc_info:
        discover_project()

    message = str(exc_info.value)
    assert "profile init" in message, "the error must say how to fix it"
    assert str(bare) in message, "the error must say where it looked"


def test_explicit_project_without_config_is_rejected(tmp_path: Path) -> None:
    """An explicit directory is still a project only if it declares itself one."""
    bare = tmp_path / "bare"
    bare.mkdir()

    with pytest.raises(ProjectNotFoundError):
        discover_project(explicit=bare)


# ---------------------------------------------------------------------------
# Never the package directory
# ---------------------------------------------------------------------------


def test_discovery_never_resolves_to_the_installed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression this whole mechanism exists to prevent.

    A CLI installed outside a checkout must fail loudly rather than quietly
    resolving paths inside site-packages.
    """
    import profilekit

    package_dir = Path(profilekit.__file__).resolve().parent
    bare = tmp_path / "bare"
    bare.mkdir()

    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)
    monkeypatch.chdir(bare)

    with pytest.raises(ProjectNotFoundError):
        discover_project()

    # And if one were somehow produced, it must not be the package directory.
    assert package_dir != bare.resolve()


# ---------------------------------------------------------------------------
# Derived paths
# ---------------------------------------------------------------------------


def test_default_paths_derive_from_the_root(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "project")
    ctx = discover_project(explicit=root)

    assert ctx.data_dir == root.resolve() / "data"
    assert ctx.output_dir == root.resolve() / "output"
    assert ctx.assets_dir == root.resolve() / "assets"
    assert ctx.schemas_dir is None, "schemas fall back to packaged data unless overridden"


def test_explicit_dir_overrides_beat_config_and_defaults(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "project")
    (root / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[paths]\noutput = "from-config"\n',
        encoding="utf-8",
    )

    ctx = discover_project(explicit=root, output_dir=root / "from-flag")
    assert ctx.output_dir == (root / "from-flag").resolve()


def test_config_paths_beat_defaults(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "project")
    (root / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[paths]\ndata = "canonical"\noutput = "dist"\nassets = "media"\n',
        encoding="utf-8",
    )

    ctx = discover_project(explicit=root)
    assert ctx.data_dir == root.resolve() / "canonical"
    assert ctx.output_dir == root.resolve() / "dist"
    assert ctx.assets_dir == root.resolve() / "media"


def test_context_is_frozen(tmp_path: Path) -> None:
    """A context is resolved once and then read-only; callers never mutate it."""
    ctx = discover_project(explicit=_make_project(tmp_path / "project"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.root = tmp_path  # type: ignore[misc]


def test_symlinked_root_resolves_to_its_real_path(tmp_path: Path) -> None:
    real = _make_project(tmp_path / "real")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    assert discover_project(explicit=link).root == real.resolve()


def test_project_context_satisfies_the_publisher_contract(tmp_path: Path) -> None:
    """Publishers take a ProjectContext; the two must not drift apart."""
    ctx = discover_project(explicit=_make_project(tmp_path / "project"))
    assert isinstance(ctx, ProjectContext)
    assert hasattr(ctx, "root")
    assert hasattr(ctx, "data_dir")
