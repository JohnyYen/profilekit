"""``profile.toml`` — parsing and validation.

The file has four sections plus a version marker:

```toml
[project]
config_version = 1

[paths]
data = "data"
output = "output"
assets = "assets"
# schemas = "schemas"   # optional; omitted means use the packaged schemas

[generators.github-readme]
greeting = "Hi 👋, I'm {name}"

[publishers.portfolio-data]
kind = "filesystem"
destination = "apps/portfolio/app/data"
```

Two validation rules point in opposite directions, deliberately.

An **unknown top-level section is an error.** Writing ``[path]`` instead of
``[paths]`` would otherwise be ignored and the tool would fall back to
defaults — the user's configuration would look accepted while doing nothing.
Silence is the worst failure mode for configuration.

An **unknown key inside a ``[generators.X]`` table passes through.** A
generator owns the validation of its own options, and a third-party generator
registered by entry point has to be configurable without the core knowing its
option names in advance.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

#: Sections the core understands. Anything else is a typo or a mistake.
KNOWN_SECTIONS = ("project", "paths", "generators", "publishers")

#: The config-file format version. Distinct from an artifact's schemaVersion:
#: this one describes the shape of profile.toml itself.
SUPPORTED_CONFIG_VERSIONS = (1,)


class ConfigError(Exception):
    """Raised when a ``profile.toml`` exists but cannot be honored."""

    exit_code = 2


def validate_config(config: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Validate a parsed config mapping, returning it unchanged on success.

    Separated from file IO so callers can validate a mapping they built
    themselves — ``profile init`` checks its own template this way.
    """
    unknown = [key for key in config if key not in KNOWN_SECTIONS]
    if unknown:
        known = ", ".join(KNOWN_SECTIONS)
        raise ConfigError(
            f"{source}: unknown top-level section(s): {', '.join(sorted(unknown))}. "
            f"Known sections are: {known}."
        )

    for section in KNOWN_SECTIONS:
        if section in config and not isinstance(config[section], dict):
            raise ConfigError(
                f"{source}: [{section}] must be a table, got {type(config[section]).__name__}"
            )

    # Each destination is a [publishers.<name>] table. A bare key such as
    # `site = "oops"` would otherwise be dropped when destinations are read,
    # and publish would report "nothing declared" with exit 0.
    for name, entry in config.get("publishers", {}).items():
        if not isinstance(entry, dict):
            raise ConfigError(
                f"{source}: [publishers.{name}] must be a table, got {type(entry).__name__}"
            )

    project = config.get("project", {})
    if "config_version" not in project:
        raise ConfigError(
            f"{source}: [project] is missing config_version; "
            f"add 'config_version = {SUPPORTED_CONFIG_VERSIONS[-1]}'"
        )

    version = project["config_version"]
    if version not in SUPPORTED_CONFIG_VERSIONS:
        supported = ", ".join(str(v) for v in SUPPORTED_CONFIG_VERSIONS)
        raise ConfigError(
            f"{source}: config_version {version} is not supported "
            f"(this build understands: {supported})"
        )

    return config


def load_config(path: Path) -> dict[str, Any]:
    """Read and validate the config file at *path*."""
    try:
        with open(path, "rb") as handle:
            parsed = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"{path}: cannot be read: {exc}") from exc

    return validate_config(parsed, source=str(path))


__all__ = [
    "KNOWN_SECTIONS",
    "SUPPORTED_CONFIG_VERSIONS",
    "ConfigError",
    "load_config",
    "validate_config",
]
