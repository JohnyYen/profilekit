"""Behavior pinned down by mutation testing of ``profilekit.context``.

The existing discovery tests move the process with ``chdir``, so the explicit
``cwd`` argument and the per-directory overrides were only exercised by
accident, depending on where the test process happened to stand. These tests
pin them independently of the process working directory (see
``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from profilekit.context import (
    CONFIG_FILENAME,
    PROJECT_ENV_VAR,
    ProjectNotFoundError,
    discover_project,
)


def _make_project(root: Path, config: str = "[project]\nconfig_version = 1\n") -> Path:
    root.mkdir(parents=True)
    (root / CONFIG_FILENAME).write_text(config, encoding="utf-8")
    return root.resolve()


@pytest.fixture(autouse=True)
def _neutral_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stand the process inside a different project, so a wrong lookup is visible."""
    monkeypatch.delenv(PROJECT_ENV_VAR, raising=False)
    decoy = _make_project(tmp_path / "decoy")
    monkeypatch.chdir(decoy)
    return decoy


def test_discovery_walks_up_from_the_given_cwd_not_the_process(tmp_path: Path) -> None:
    project = _make_project(tmp_path / "project")
    nested = project / "src" / "deep"
    nested.mkdir(parents=True)

    assert discover_project(cwd=nested).root == project


def test_an_env_var_without_a_config_is_named_in_the_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv(PROJECT_ENV_VAR, str(empty))

    with pytest.raises(ProjectNotFoundError) as excinfo:
        discover_project()

    assert str(excinfo.value) == (
        f"{PROJECT_ENV_VAR} points at {empty.resolve()}, which has no {CONFIG_FILENAME}"
    )


def test_explicit_data_and_assets_directories_override_the_config(tmp_path: Path) -> None:
    project = _make_project(tmp_path / "project")
    data = tmp_path / "elsewhere" / "data"
    assets = tmp_path / "elsewhere" / "assets"

    ctx = discover_project(project, data_dir=data, assets_dir=assets)

    assert ctx.data_dir == data.resolve()
    assert ctx.assets_dir == assets.resolve()


def test_empty_configured_paths_fall_back_to_the_conventions(tmp_path: Path) -> None:
    config = '[project]\nconfig_version = 1\n\n[paths]\ndata = ""\nschemas = ""\n'
    project = _make_project(tmp_path / "project", config)

    ctx = discover_project(project)

    assert ctx.data_dir == project / "data"
    assert ctx.schemas_dir is None
