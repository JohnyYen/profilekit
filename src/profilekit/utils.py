"""Shared utilities for all profile data generators."""

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"


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


def load_json_strict(
    filename: str,
    data_dir: Path,
    required_fields: tuple[str, ...] = (),
) -> dict | list:
    """Load *filename* from *data_dir*, raising DataError for known faults.

    Raises:
        DataError: if the file is missing, contains invalid JSON, or is missing
            any of the *required_fields*.

    Unlike ``load_json``, this function never calls ``sys.exit`` — callers
    receive a typed exception with file/field context.
    """
    path = data_dir / filename
    if not path.exists():
        raise DataError(filename, message="data file not found")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise DataError(
            filename, message=f"JSON parse error at line {exc.lineno}: {exc.msg}"
        ) from exc

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
    """Load a JSON file from data_dir; exits with code 1 if the file is missing."""
    path = data_dir / filename
    if not path.exists():
        print(f"ERROR: Missing data file: {filename}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_output(content: str, output_dir: Path, filename: str) -> Path:
    """Write content to output_dir/filename, creating parent directories as needed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


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
