"""Project scaffolding for ``profile init``.

The example profile here belongs to a deliberately fictional person. That is
not decoration: a scaffold seeded with the maintainer's name, email, or
handles would ship one person's details into every project created from it,
and the first thing a new user would discover is that their CV carries
somebody else's name.

Ada Lovelace is used because she is unmistakably an example — nobody mistakes
the scaffold for their own data, which is exactly the property a placeholder
needs.

The example data is also valid against the shipped schemas as written. A
scaffold that fails its own validator teaches the user the tool is broken
before they have changed anything.
"""

from __future__ import annotations

import json
from pathlib import Path

from profilekit.context import CONFIG_FILENAME
from profilekit.safe_io import write_file

PROFILE_TOML = """\
# profilekit project configuration.
# See the documentation for every available option.

[project]
config_version = 1

[paths]
data = "data"
output = "output"
assets = "assets"

# A destination binds a name to a publisher kind. `filesystem` writes into a
# directory inside this project — point it at whatever frontend reads the
# generated JSON.
#
# [publishers.site-data]
# kind = "filesystem"
# destination = "site/src/data"

# Some platforms expose no write API for profile fields. A `manual`
# destination emits its artifact and reports the pending action rather than
# claiming a publish it never performed.
#
# [publishers.linkedin]
# kind = "manual"
# artifacts = ["linkedin.md"]
"""

ABOUT = {
    "username": "Ada Lovelace",
    "headline": "Mathematician | Analytical Engine Programmer",
    "tagline": "Writing algorithms for machines that do not exist yet",
    "description": (
        "Mathematician working on general-purpose computation. Interested in "
        "symbolic manipulation, the limits of mechanical reasoning, and "
        "notation that makes hard ideas teachable."
    ),
    "location": "London, England",
    "email": "ada@example.com",
    "languages": ["English", "French"],
    "currentFocus": [
        {
            "title": "General-purpose computation",
            "description": "Showing the engine can operate on symbols, not just numbers.",
        },
        {
            "title": "Algorithm notation",
            "description": "Describing a computation precisely enough to be executed.",
        },
    ],
    "whatIBuild": [
        "Algorithms for mechanical computation",
        "Annotated translations of technical papers",
        "Notation for describing programs",
    ],
    "learningJourney": (
        "Replace this with what you are learning right now. It is the section "
        "people read most and the easiest one to leave stale."
    ),
}

SOCIAL = {
    "github": "https://github.com/example",
    "linkedin": "https://linkedin.com/in/example",
    "email": "ada@example.com",
}

EXPERIENCE = [
    {
        "company": "Analytical Engine Project",
        "position": "Collaborator",
        "start_date": "1842-01",
        "end_date": "1843-12",
        "location": "London, England",
        "summary": "Translated and annotated the first description of a general-purpose computer.",
        "highlights": [
            "Wrote Note G, the first published algorithm intended for a machine.",
            "Argued the engine could manipulate symbols, not only numbers.",
        ],
    }
]

EDUCATION = [
    {
        "institution": "Private tuition",
        "area": "Mathematics",
        "degree": "Independent study",
        "start_date": "1829-01",
        "end_date": "1840-12",
        "location": "London, England",
        "highlights": [
            "Studied mathematics and logic under Mary Somerville and Augustus De Morgan."
        ],
    }
]

PROJECTS = [
    {
        "name": "Note G",
        "description": "An algorithm for computing Bernoulli numbers on the Analytical Engine.",
        "tech": "Analytical Engine",
        "url": "https://example.com/note-g",
    }
]

SKILLS = {
    "categories": [
        {"label": "Mathematics", "details": ["Analysis", "Number theory", "Symbolic logic"]},
        {"label": "Writing", "details": ["Technical translation", "Annotation"]},
    ]
}

EXAMPLE_DATA: dict[str, object] = {
    "about.json": ABOUT,
    "social.json": SOCIAL,
    "experience.json": EXPERIENCE,
    "education.json": EDUCATION,
    "projects.json": PROJECTS,
    "skills.json": SKILLS,
}


class ScaffoldError(Exception):
    """Raised when a project cannot be scaffolded at the requested location."""

    exit_code = 1


def init_project(target: Path) -> list[Path]:
    """Scaffold a project at *target*, returning the files written.

    Refuses to proceed when a configuration file or any example data file
    already exists. Re-running ``init`` over a configured project, or over a
    directory that already holds profile data, would silently discard whatever
    the user had set up, and losing data is worse than an error message. Every
    destination is checked before the first write, so a refusal leaves the
    directory untouched.
    """
    target = Path(target)
    config_path = target / CONFIG_FILENAME
    data_dir = target / "data"

    if config_path.exists():
        raise ScaffoldError(
            f"{config_path} already exists; this directory is already a profilekit project"
        )
    existing = [data_dir / name for name in EXAMPLE_DATA if (data_dir / name).exists()]
    if existing:
        names = ", ".join(str(path) for path in existing)
        raise ScaffoldError(f"refusing to overwrite existing profile data: {names}")

    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # overwrite=False: the checks above give the friendly message; the helper
    # still refuses a file that appears between them and the write.
    written.append(write_file(config_path, PROFILE_TOML, root=target, overwrite=False))

    data_dir.mkdir(exist_ok=True)
    for filename, payload in EXAMPLE_DATA.items():
        content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        written.append(write_file(data_dir / filename, content, root=target, overwrite=False))

    return written


__all__ = ["EXAMPLE_DATA", "PROFILE_TOML", "ScaffoldError", "init_project"]
