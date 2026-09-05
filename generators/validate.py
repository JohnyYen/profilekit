#!/usr/bin/env python3
"""Validate all data/*.json files against schemas/*.schema.json using jsonschema."""

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
SCHEMAS_DIR = ROOT_DIR / "schemas"

# Map of data file stem → schema file name (all under DATA_DIR / SCHEMAS_DIR)
_SCHEMA_MAP = {
    "about": "about.schema.json",
    "social": "social.schema.json",
    "experience": "experience.schema.json",
    "education": "education.schema.json",
    "projects": "projects.schema.json",
    "skills": "skills.schema.json",
}

REQUIRED_FILES = [f"{stem}.json" for stem in _SCHEMA_MAP]


def _load_json(path: Path) -> Any:
    """Load raw JSON from *path*."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_file(data_file: str) -> tuple[bool, list[str]]:
    """Validate *data_file* against its JSON Schema. Returns (passed, errors).

    Errors include the file name and the jsonschema validation message so
    callers can produce a meaningful FAIL line.

    ``DATA_DIR`` and ``SCHEMAS_DIR`` are module-level names — tests can
    monkeypatch them to point at fixtures without touching the filesystem.
    """
    stem = data_file.replace(".json", "")
    schema_name = _SCHEMA_MAP.get(stem, f"{stem}.schema.json")
    schema_path = SCHEMAS_DIR / schema_name
    data_path = DATA_DIR / data_file

    if not schema_path.exists():
        return False, [f"Schema file not found: {schema_path}"]
    if not data_path.exists():
        return False, [f"Data file not found: {data_path}"]

    try:
        schema = _load_json(schema_path)
        data = _load_json(data_path)
    except json.JSONDecodeError as exc:
        return False, [f"{data_file}: JSON parse error: {exc}"]

    validator = jsonschema.Draft7Validator(schema)
    raw_errors = sorted(validator.iter_errors(data), key=str)
    errors = []
    for err in raw_errors:
        path = ".".join(str(p) for p in err.absolute_path)
        location = f" at {path}" if path else ""
        errors.append(f"{data_file}{location}: {err.message}")
    return len(errors) == 0, errors


MAX_PORTFOLIO_HIGHLIGHTS = 6


def validate_portfolio_highlights(about: dict, projects: list) -> list[str]:
    """Validate portfolioHighlights against known project names.

    Returns a list of warning strings (empty = no warnings).
    Checks:
    - Each highlight name must match a project name in ``projects``.
    - The list should not exceed MAX_PORTFOLIO_HIGHLIGHTS entries.
    Non-fatal: warnings are returned, not raised.
    """
    highlights = about.get("portfolioHighlights")
    if not highlights:
        return []

    project_names = {p["name"] for p in projects}
    warnings = []

    if len(highlights) > MAX_PORTFOLIO_HIGHLIGHTS:
        warnings.append(
            f"portfolioHighlights has {len(highlights)} entries; "
            f"only {MAX_PORTFOLIO_HIGHLIGHTS} are recommended."
        )

    for name in highlights:
        if name not in project_names:
            warnings.append(
                f"portfolioHighlights: '{name}' does not match any project in projects.json."
            )

    return warnings


def main() -> int:
    """Validate all data files; return 0 on success, 1 on any failure."""
    print("=" * 60)
    print("Profile Data Validation")
    print("=" * 60)
    print()

    all_passed = True
    results = []

    for filename in REQUIRED_FILES:
        passed, errors = validate_file(filename)
        status = "PASS" if passed else "FAIL"
        results.append((filename, status, errors))
        if not passed:
            all_passed = False

    # Print summary table
    print(f"{'File':<30} {'Status':<10}")
    print("-" * 40)
    for filename, status, errors in results:
        print(f"{filename:<30} {status:<10}")
        for err in errors:
            print(f"  ERROR: {err}")

    print()

    # Cross-file: validate portfolioHighlights against projects.json
    about_path = DATA_DIR / "about.json"
    projects_path = DATA_DIR / "projects.json"
    if about_path.exists() and projects_path.exists():
        try:
            about_data = _load_json(about_path)
            projects_data = _load_json(projects_path)
            highlight_warnings = validate_portfolio_highlights(about_data, projects_data)
            for warning in highlight_warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
        except Exception as exc:
            print(f"WARNING: Could not validate portfolioHighlights: {exc}", file=sys.stderr)

    # Icon reachability (non-fatal, skippable)
    try:
        from generators.icons import check_icons  # noqa: PLC0415

        skills_path = DATA_DIR / "skills.json"
        if skills_path.exists():
            skills_data = _load_json(skills_path)
            icon_warnings = check_icons(skills_data)
            for warning in icon_warnings:
                print(f"WARNING (icon): {warning}", file=sys.stderr)
    except ImportError:
        # icons.py not yet present — skip silently
        pass

    # Link reachability (non-fatal, skippable)
    try:
        from generators.links import check_links  # noqa: PLC0415

        projects_path = DATA_DIR / "projects.json"
        social_path = DATA_DIR / "social.json"
        projects_data = _load_json(projects_path) if projects_path.exists() else []
        social_data = _load_json(social_path) if social_path.exists() else {}
        link_warnings = check_links(projects_data, social_data)
        for warning in link_warnings:
            print(f"WARNING (link): {warning}", file=sys.stderr)
    except ImportError:
        # links.py not yet present — skip silently
        pass

    if all_passed:
        print("All validations passed!")
        return 0
    else:
        print("Some validations FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
