"""Shared pytest fixtures for the profile-data test suite."""

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the tests/fixtures/ directory."""
    return FIXTURES_DIR


def make_about(overrides: dict | None = None) -> dict:
    """Return a minimal valid about dict merged with overrides."""
    base = {
        "username": "testuser",
        "tagline": "Test tagline",
        "description": "Test description.",
    }
    if overrides:
        base.update(overrides)
    return base


def make_projects(names: list[str] | None = None) -> list[dict]:
    """Return a list of project dicts with only the name field."""
    if names is None:
        names = []
    return [{"name": n} for n in names]
