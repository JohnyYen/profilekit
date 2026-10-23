"""`pyproject.toml` PEP 621 metadata completeness (spec `package-distribution`,
Req: Publishable package metadata).

A package with no description, license, classifiers, or project URLs cannot
be meaningfully published to PyPI — this guards that the fields a third-party
index page needs are actually filled in, not left at scaffold defaults.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_NON_EMPTY_FIELDS = [
    "description",
    "readme",
    "license",
    "authors",
    "keywords",
    "classifiers",
]


def _load_pyproject() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_required_fields_present_and_non_empty():
    project = _load_pyproject()["project"]
    missing_or_empty = [field for field in REQUIRED_NON_EMPTY_FIELDS if not project.get(field)]
    assert not missing_or_empty, (
        f"pyproject.toml [project] is missing or has empty: {missing_or_empty}"
    )


def test_project_urls_present_and_non_empty():
    project = _load_pyproject()["project"]
    urls = project.get("urls")
    assert urls, "pyproject.toml [project.urls] must be present and non-empty"
    assert all(urls.values()), "every [project.urls] entry must have a non-empty value"


def test_authors_have_name_and_email():
    project = _load_pyproject()["project"]
    authors = project["authors"]
    assert authors, "authors must be non-empty"
    for author in authors:
        assert author.get("name"), f"author entry missing name: {author}"
        assert author.get("email"), f"author entry missing email: {author}"


def _requirement_floor(requirement: str, name: str) -> tuple[int, ...] | None:
    """Return the `>=` floor of `name` in a PEP 508 requirement, if it is one."""
    head, sep, version = requirement.partition(">=")
    if head.strip() != name or not sep:
        return None
    return tuple(int(part) for part in version.split(",")[0].strip().split("."))


def test_build_backend_floor_supports_spdx_license_expression():
    """A string `license` is a PEP 639 SPDX expression, which setuptools only
    accepts from 77. A lower floor lets an older backend reject the build."""
    data = _load_pyproject()
    assert isinstance(data["project"]["license"], str), "license is expected in PEP 639 form"
    floors = [
        floor
        for requirement in data["build-system"]["requires"]
        if (floor := _requirement_floor(requirement, "setuptools")) is not None
    ]
    assert floors, "build-system.requires must pin a setuptools floor with >="
    assert floors[0] >= (77,), f"setuptools floor {floors[0]} predates PEP 639 support (77)"


def test_no_license_classifier_alongside_spdx_expression():
    """PEP 639 forbids a `License ::` classifier next to an SPDX `license`;
    newer setuptools rejects the combination outright."""
    project = _load_pyproject()["project"]
    license_classifiers = [c for c in project["classifiers"] if c.startswith("License ::")]
    assert license_classifiers == []
