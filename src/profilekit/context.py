"""Project discovery — deciding which project ``profile`` is acting on.

Every path this tool reads or writes hangs off a ``ProjectContext``, and a
context is resolved from the *caller's* world: an explicit flag, an environment
variable, or a ``profile.toml`` found by walking up from the working directory.

It is never derived from ``__file__``. That distinction is the whole point. When
paths came from the package's own location, an installed CLI resolved ``data/``
inside ``site-packages``, so the tool only worked from inside a clone of one
particular repository — which made it unusable as a package and untestable
without monkeypatching module globals.

There is deliberately no fallback to the working directory. A tool that guesses
the project when it cannot find one writes generated files somewhere the user
did not ask for. Failing with an actionable message is the better outcome.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from profilekit.config import ConfigError, load_config

CONFIG_FILENAME = "profile.toml"
PROJECT_ENV_VAR = "PROFILEKIT_PROJECT"

DEFAULT_DATA_DIR = "data"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_ASSETS_DIR = "assets"


class ProjectNotFoundError(Exception):
    """Raised when no project could be resolved.

    Carries the exit code the CLI should use, so the caller does not have to
    remember which number means "the user needs to do something".
    """

    exit_code = 2


@dataclass(frozen=True)
class ProjectContext:
    """The resolved project a command operates on.

    ``root`` is always a real, symlink-resolved path. ``schemas_dir`` is
    ``None`` unless the project overrides it, in which case the packaged
    schemas shipped with the distribution are used instead.
    """

    root: Path
    data_dir: Path
    output_dir: Path
    assets_dir: Path
    schemas_dir: Path | None = None
    config: dict[str, Any] | None = None

    def generator_options(self, name: str) -> dict[str, Any]:
        """Return the ``[generators.<name>]`` table, or an empty one.

        Generators own the validation of their own options, so unknown keys
        inside their table are passed through rather than rejected here.
        """
        config = self.config or {}
        generators = config.get("generators")
        if not isinstance(generators, dict):
            return {}
        options = generators.get(name)
        return dict(options) if isinstance(options, dict) else {}

    def publisher_destinations(self) -> dict[str, dict[str, Any]]:
        """Return the ``[publishers.*]`` tables keyed by destination name."""
        config = self.config or {}
        publishers = config.get("publishers")
        if not isinstance(publishers, dict):
            return {}
        return {name: dict(table) for name, table in publishers.items() if isinstance(table, dict)}


def _find_upwards(start: Path) -> Path | None:
    """Return the nearest ancestor of *start* containing a config file.

    The walk resolves symlinks first so a linked working directory cannot
    escape into an unrelated tree, and stops at the filesystem root.
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / CONFIG_FILENAME).is_file():
            return candidate
    return None


def _resolve_root(explicit: Path | None, cwd: Path | None) -> Path:
    """Resolve the project root by precedence, or fail.

    Precedence: explicit argument, then ``PROFILEKIT_PROJECT``, then the
    nearest ``profile.toml`` above the working directory.
    """
    if explicit is not None:
        root = Path(explicit).resolve()
        if not (root / CONFIG_FILENAME).is_file():
            raise ProjectNotFoundError(
                f"no {CONFIG_FILENAME} in {root}; run 'profile init' to create one"
            )
        return root

    from_env = os.environ.get(PROJECT_ENV_VAR)
    if from_env:
        root = Path(from_env).resolve()
        if not (root / CONFIG_FILENAME).is_file():
            raise ProjectNotFoundError(
                f"{PROJECT_ENV_VAR} points at {root}, which has no {CONFIG_FILENAME}"
            )
        return root

    start = Path(cwd) if cwd is not None else Path.cwd()
    found = _find_upwards(start)
    if found is None:
        raise ProjectNotFoundError(
            f"no {CONFIG_FILENAME} found in {start} or any parent; run 'profile init'"
        )
    return found


def _path_from(root: Path, configured: object, default: str) -> Path:
    """Resolve one configured path against *root*, falling back to *default*."""
    if isinstance(configured, str) and configured:
        return (root / configured).resolve()
    return (root / default).resolve()


def discover_project(
    explicit: Path | None = None,
    *,
    cwd: Path | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> ProjectContext:
    """Resolve the project context.

    The root follows the precedence in this module's docstring. Individual
    directories follow the same shape one level down: an explicit argument
    beats ``[paths]`` in ``profile.toml``, which beats the convention.
    """
    root = _resolve_root(explicit, cwd)
    config = load_config(root / CONFIG_FILENAME)

    paths = config.get("paths")
    paths = paths if isinstance(paths, dict) else {}

    schemas = paths.get("schemas")
    schemas_dir = (root / schemas).resolve() if isinstance(schemas, str) and schemas else None

    return ProjectContext(
        root=root,
        data_dir=(
            Path(data_dir).resolve()
            if data_dir is not None
            else _path_from(root, paths.get("data"), DEFAULT_DATA_DIR)
        ),
        output_dir=(
            Path(output_dir).resolve()
            if output_dir is not None
            else _path_from(root, paths.get("output"), DEFAULT_OUTPUT_DIR)
        ),
        assets_dir=(
            Path(assets_dir).resolve()
            if assets_dir is not None
            else _path_from(root, paths.get("assets"), DEFAULT_ASSETS_DIR)
        ),
        schemas_dir=schemas_dir,
        config=config,
    )


__all__ = [
    "CONFIG_FILENAME",
    "PROJECT_ENV_VAR",
    "ConfigError",
    "ProjectContext",
    "ProjectNotFoundError",
    "discover_project",
]
