"""Shared utilities for the profilekit generators.

Every path-taking helper here receives its directory explicitly. There are
deliberately no module-level path constants: a helper that resolves its own
destination cannot be redirected, and one derived from ``__file__`` resolves
inside the installed package rather than the user's project.
"""

import json
import sys
from pathlib import Path
from typing import Any

from profilekit.safe_io import write_file

# ---------------------------------------------------------------------------
# Typed error for known data faults (missing file/field, malformed JSON)
# ---------------------------------------------------------------------------


class DataError(Exception):
    """Raised for known data faults with file and optional field context.

    Attributes:
        file: the data file that caused the error (relative name, e.g. "about.json").
        field: the missing/invalid field name, or None if not applicable.
    """

    def __init__(self, file: str, field: str | None = None, message: str = "") -> None:
        self.file = file
        self.field = field
        detail = f" (field: '{field}')" if field else ""
        full_message = f"{file}{detail}: {message}" if message else f"{file}{detail}"
        super().__init__(full_message)


def _parse(path: Path, filename: str) -> Any:
    """Parse the JSON at *path*, raising DataError that names *filename*.

    A parse error carries its line and column, so the user can go straight to
    the fault; bytes that are not UTF-8 are a data fault of the same kind.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise DataError(
            filename,
            message=f"JSON parse error at line {exc.lineno} column {exc.colno}: {exc.msg}",
        ) from exc
    except UnicodeDecodeError as exc:
        raise DataError(filename, message=f"not valid UTF-8 ({exc.reason})") from exc


def load_json_strict(
    filename: str,
    data_dir: Path,
    required_fields: tuple[str, ...] = (),
) -> dict | list:
    """Load *filename* from *data_dir*, raising DataError for known faults.

    Raises:
        DataError: if the file is missing, contains invalid JSON, holds a
            top-level value that is not an object or array, or is missing
            any of the *required_fields*.

    Unlike ``load_json``, this function never calls ``sys.exit`` — callers
    receive a typed exception with file/field context.
    """
    path = data_dir / filename
    if not path.exists():
        raise DataError(filename, message="data file not found")

    data = _parse(path, filename)
    if not isinstance(data, (dict, list)):
        raise DataError(filename, message="expected a JSON object or array at the top level")

    if required_fields and isinstance(data, dict):
        for field in required_fields:
            if field not in data:
                raise DataError(filename, field=field, message="missing required field")

    return data


def run(main_fn) -> None:
    """Call *main_fn*(), catching DataError for clean exit.

    - DataError → prints the message to stderr and calls sys.exit(1).
    - Any other exception is re-raised unchanged (tracebacks surface normally).
    """
    try:
        main_fn()
    except DataError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def what_i_build(about: dict, platform: str) -> list[str]:
    """Return the "what I build" bullet list for *platform*.

    Lookup order:
    1. ``about["whatIBuildVariants"][platform]`` — if the key exists, is a
       non-null mapping, and the platform key is non-null, wrap the value in a
       list and return it.
    2. ``about["whatIBuild"]`` — fall back to the generic list.
    3. ``[]`` — if neither is present.

    This function never raises on absent or null keys.
    """
    variants = about.get("whatIBuildVariants")
    if variants and isinstance(variants, dict):
        platform_value = variants.get(platform)
        if platform_value is not None:
            return [platform_value] if isinstance(platform_value, str) else list(platform_value)
    return list(about.get("whatIBuild") or [])


def load_json(filename: str, data_dir: Path) -> Any:
    """Load a JSON file from data_dir; exits with code 1 if the file is missing.

    Raises:
        DataError: if the file is not valid JSON, naming the file and the
            line and column of the fault.
    """
    path = data_dir / filename
    if not path.exists():
        print(f"ERROR: Missing data file: {filename}", file=sys.stderr)
        sys.exit(1)
    return _parse(path, filename)


def write_output(content: str, output_dir: Path, filename: str) -> Path:
    """Write content to output_dir/filename, creating output_dir as needed.

    Generated output is meant to be regenerated, so an existing file is
    replaced; the write is still refused through a symlink or out of
    *output_dir* (see :mod:`profilekit.safe_io`).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return write_file(output_dir / filename, content, root=output_dir, overwrite=True)


def skill_name(entry: str | dict) -> str:
    """Return the display name for a skill entry.

    Accepts either a plain string or an object dict with at least a 'name' key.
    Plain strings are returned unchanged; dicts return their 'name' value.
    """
    if isinstance(entry, str):
        return entry
    return entry["name"]


def skill_icon(entry: str | dict) -> tuple[str | None, str | None] | None:
    """Return the icon references for a skill entry as (slug, iconUrl).

    - Plain string entry: returns None (no icon information available).
    - Object with 'iconUrl': returns (None, iconUrl) — iconUrl takes priority.
    - Object with 'icon' only: returns (slug, None).
    - Object with neither: returns (None, None).
    """
    if isinstance(entry, str):
        return None
    icon_url = entry.get("iconUrl")
    if icon_url:
        return (None, icon_url)
    slug = entry.get("icon")
    return (slug, None) if slug else (None, None)
