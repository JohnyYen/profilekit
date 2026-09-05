"""Tests for generators/icons.py — check_icons reachability helper.

All tests must fail before icons.py exists.
"""

import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal skills fixture
# ---------------------------------------------------------------------------

def _skills_with_slug(slug: str) -> dict:
    return {
        "categories": [
            {"label": "Backend", "details": [{"name": "MyLib", "icon": slug}]}
        ]
    }


def _skills_with_icon_url(url: str) -> dict:
    return {
        "categories": [
            {"label": "Backend", "details": [{"name": "MyLib", "iconUrl": url}]}
        ]
    }


# ---------------------------------------------------------------------------
# (a) offline=True → returns [] and makes no network calls
# ---------------------------------------------------------------------------

def test_check_icons_offline_returns_empty():
    """check_icons(skills, offline=True) returns [] without any network I/O."""
    from generators.icons import check_icons

    skills = _skills_with_slug("nestjs")

    with patch("urllib.request.urlopen") as mock_open:
        warnings = check_icons(skills, offline=True)

    assert warnings == []
    mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# (b) mocked urlopen returning status 200 → no warnings
# ---------------------------------------------------------------------------

def test_check_icons_200_ok_no_warnings(monkeypatch):
    """A 200 response from urlopen produces no warnings."""
    from generators.icons import check_icons

    # Ensure SKIP_ICON_CHECK does not interfere with this test
    monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)

    skills = _skills_with_slug("nestjs")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        warnings = check_icons(skills)

    assert warnings == []


# ---------------------------------------------------------------------------
# (c) non-200 response → list contains warning string with slug/URL
# ---------------------------------------------------------------------------

def test_check_icons_non_200_produces_warning(monkeypatch):
    """A non-200 HTTP response produces a warning mentioning the slug."""
    from generators.icons import check_icons

    # Ensure SKIP_ICON_CHECK does not interfere with this test
    monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)

    skills = _skills_with_slug("unknown-slug")

    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        warnings = check_icons(skills)

    assert len(warnings) >= 1
    assert any("unknown-slug" in w or "404" in w for w in warnings)


# ---------------------------------------------------------------------------
# (d) urllib.error.URLError (timeout) → warning produced, no exception raised
# ---------------------------------------------------------------------------

def test_check_icons_url_error_produces_warning_no_exception(monkeypatch):
    """A URLError (e.g. timeout) produces a warning and does NOT raise."""
    from generators.icons import check_icons

    # Ensure SKIP_ICON_CHECK does not interfere with this test
    monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)

    skills = _skills_with_slug("nestjs")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        warnings = check_icons(skills)

    assert len(warnings) >= 1
    assert any("nestjs" in w or "timed out" in w or "URLError" in w for w in warnings)


# ---------------------------------------------------------------------------
# (e) SKIP_ICON_CHECK=1 env var → returns [] without network
# ---------------------------------------------------------------------------

def test_check_icons_skip_env_var(monkeypatch):
    """SKIP_ICON_CHECK=1 env var causes check_icons to skip entirely."""
    from generators.icons import check_icons

    monkeypatch.setenv("SKIP_ICON_CHECK", "1")
    skills = _skills_with_slug("nestjs")

    with patch("urllib.request.urlopen") as mock_open:
        warnings = check_icons(skills)

    assert warnings == []
    mock_open.assert_not_called()
