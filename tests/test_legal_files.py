"""Legal and community file presence (spec `package-distribution`, Req:
Legal and community files present).

A third party running `pip install` needs these at the repository root before
the package can be considered open-source-ready.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
]

# A conservative set of recognizable OSI license markers. We only need to
# confirm LICENSE names a real, recognized license — not parse SPDX exactly.
OSI_LICENSE_MARKERS = [
    "MIT License",
    "Apache License",
    "GNU GENERAL PUBLIC LICENSE",
    "BSD",
    "Mozilla Public License",
]


def test_required_legal_files_present():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"missing required root files: {missing}"


def test_license_names_osi_license():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.strip(), "LICENSE must not be empty"
    assert any(marker in license_text for marker in OSI_LICENSE_MARKERS), (
        "LICENSE must name a recognized OSI-approved license"
    )


def test_license_is_not_a_vendored_skill_license():
    """LICENSE must belong to this project, not a vendored skill/tool."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    # Vendored skill licenses (e.g. agent-skill scaffolding) typically name a
    # third-party tool/organization in their copyright line, not this project.
    assert "gentleman-programming" not in license_text.lower()
    assert "anthropic" not in license_text.lower()
