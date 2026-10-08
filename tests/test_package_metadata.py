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
    missing_or_empty = [
        field
        for field in REQUIRED_NON_EMPTY_FIELDS
        if not project.get(field)
    ]
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
