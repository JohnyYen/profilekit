"""The test suite must not carry a real person's details.

Fixtures and snapshots get read by every contributor, copied into bug reports,
and indexed by every code search engine that crawls a public repository. A
suite seeded with the maintainer's email and phone number publishes those
things far more durably than the profile data itself does, and for no benefit:
a generator does not care whose name it formats.

``data/`` is excluded on purpose. That is the owner's profile, deliberately
public, and publishing it is the entire point of the project. This rule is
about *test* material, which has no reason to be real.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

#: Identity that must not appear in test material. Lowercased before matching.
DENY_LIST = (
    "johny",
    "pedraza",
    "romero",
    "johnyyen",
    "bernalsuarez",
    "+53",
    "55002026",
    "johny.antonio.pedraza.romero",
)

#: This file necessarily contains the deny-list itself.
EXEMPT = {"test_no_real_pii.py"}

TEXT_SUFFIXES = {".py", ".json", ".md", ".yml", ".yaml", ".toml", ".txt"}


def _test_material() -> list[Path]:
    return [
        path
        for path in sorted(TESTS_DIR.rglob("*"))
        if path.is_file()
        and path.suffix in TEXT_SUFFIXES
        and path.name not in EXEMPT
        and "__pycache__" not in path.parts
    ]


def test_there_is_test_material_to_check() -> None:
    """Guard the guard: an empty sweep would pass while proving nothing."""
    assert len(_test_material()) > 10


@pytest.mark.parametrize("marker", DENY_LIST)
def test_no_real_pii_in_test_material(marker: str) -> None:
    """No maintainer identity anywhere under tests/."""
    offenders: list[str] = []

    for path in _test_material():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if marker in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, (
        f"{marker!r} appears in test material: {offenders}. "
        "Fixtures and snapshots must use a fictional persona."
    )
