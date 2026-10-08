"""Tests for profilekit/links.py — check_links reachability helper.

All tests must fail before links.py exists (RED).
"""

import urllib.error
from unittest.mock import MagicMock, patch


def _projects(url: str) -> list:
    return [{"name": "MyProject", "url": url}]


def _social(**kwargs) -> dict:
    return kwargs


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.status = 200
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# (a) offline=True → [] with no network I/O
def test_check_links_offline_returns_empty():
    from profilekit.links import check_links

    with patch("urllib.request.urlopen") as mock_open:
        warnings = check_links(_projects("https://example.com"), _social(), offline=True)

    assert warnings == []
    mock_open.assert_not_called()


# (b) SKIP_LINK_CHECK=1 env var → [] with no network I/O
def test_check_links_skip_env_var(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.setenv("SKIP_LINK_CHECK", "1")

    with patch("urllib.request.urlopen") as mock_open:
        warnings = check_links(_projects("https://example.com"), _social())

    assert warnings == []
    mock_open.assert_not_called()


# (c) empty project URL → warning mentioning the project name, no network call
def test_check_links_empty_project_url_warns(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    with patch("urllib.request.urlopen") as mock_open:
        warnings = check_links(_projects(""), _social())

    assert any("MyProject" in w for w in warnings)
    mock_open.assert_not_called()


# (d) reachable (200) project + social URLs → no warnings
def test_check_links_200_ok_no_warnings(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    with patch("urllib.request.urlopen", return_value=_ok_response()):
        warnings = check_links(
            _projects("https://example.com"),
            _social(github="https://github.com/x"),
        )

    assert warnings == []


# (e) non-200 response → warning produced
def test_check_links_non_200_warns(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    resp = MagicMock()
    resp.status = 404
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=resp):
        warnings = check_links(_projects("https://example.com/missing"), _social())

    assert len(warnings) >= 1
    assert any("404" in w or "MyProject" in w for w in warnings)


# (f) URLError → warning, no exception raised
def test_check_links_url_error_no_exception(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        warnings = check_links(_projects("https://example.com"), _social())

    assert len(warnings) >= 1


# (g) non-http social values (e.g. email) are ignored, not checked
def test_check_links_ignores_non_http_social(monkeypatch):
    from profilekit.links import check_links

    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        warnings = check_links([], _social(email="john@example.com"))

    assert warnings == []
    mock_open.assert_not_called()
