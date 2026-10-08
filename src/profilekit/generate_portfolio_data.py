#!/usr/bin/env python3
"""Generate portfolio app data files from canonical profile data.

Reads canonical data/*.json and writes app-consumed JSON shapes into
apps/portfolio/app/data/. This generator writes OUTSIDE output/ deliberately;
its output path is the Next.js app data directory, not the output/ directory.
"""

import json
from pathlib import Path

from profilekit.utils import load_json, run, write_output

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"

# Single fixed output path — no dynamic input. This constant is the threat-boundary
# anchor: tests assert no writes occur outside this directory.
PORTFOLIO_DATA_DIR = ROOT_DIR / "apps" / "portfolio" / "app" / "data"

_ABOUT_KEYS = (
    "username",
    "tagline",
    "description",
    "currentFocus",
    "whatIBuild",
    "learningJourney",
)


def build_about(about: dict) -> dict:
    """Return the 6-key subset of canonical about data consumed by the portfolio app."""
    return {key: about[key] for key in _ABOUT_KEYS}


def build_social(social: dict) -> dict:
    """Return a full passthrough copy of canonical social data."""
    return dict(social)


def build_skills(skills: dict) -> dict:
    """Return a full passthrough copy of canonical skills data."""
    return dict(skills)


def build_projects(projects: list) -> list:
    """Map canonical projects list to the app's GitHub-fallback shape.

    Each entry is reduced to {name, description, tech, url}; optional fields
    default to "" when absent. Canonical-only fields (start_date, end_date,
    highlights) are dropped. Source order is preserved.
    """
    return [
        {
            "name": p["name"],
            "description": p.get("description", ""),
            "tech": p.get("tech", ""),
            "url": p.get("url", ""),
        }
        for p in projects
    ]


def main() -> None:
    """Load canonical data, apply transforms, and write four JSON files."""
    about_raw = load_json("about.json", DATA_DIR)
    social_raw = load_json("social.json", DATA_DIR)
    skills_raw = load_json("skills.json", DATA_DIR)
    projects_raw = load_json("projects.json", DATA_DIR)

    outputs = {
        "about.json": build_about(about_raw),
        "social.json": build_social(social_raw),
        "skills.json": build_skills(skills_raw),
        "projects.json": build_projects(projects_raw),
    }

    for filename, data in outputs.items():
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        write_output(content, PORTFOLIO_DATA_DIR, filename)

    print(f"Generated portfolio app data in {PORTFOLIO_DATA_DIR}")


if __name__ == "__main__":
    run(main)
