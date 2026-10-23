"""Link validation helper — stdlib only (urllib), no requests dependency.

``check_links`` validates the http(s) URLs found in ``projects.json`` and
``social.json``. Empty project URLs and unreachable / non-200 URLs produce
warning strings; the function never raises. It is fully skippable via
``SKIP_LINK_CHECK=1`` or the ``offline`` keyword argument.

The reachability probe mirrors ``profilekit.icons`` (HEAD, GET fallback on 405).
"""

import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_DEFAULT_TIMEOUT = 5  # seconds


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _check_url(label: str, url: str, timeout: int) -> str | None:
    """Return a warning string if the URL is not reachable; else None.

    Uses HEAD first; falls back to GET on HTTP 405 Method Not Allowed. A URL
    that is not http(s) is reported without being opened: urllib would read a
    ``file:`` URL from local disk, and raises ``ValueError`` for a string with
    no scheme at all.
    """
    if urllib.parse.urlsplit(url).scheme.lower() not in ("http", "https"):
        return f"Link is not an http(s) URL: {label} — {url}"
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return f"Link not reachable (HTTP {resp.status}): {label} — {url}"
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            get_req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                    if resp.status != 200:
                        return f"Link not reachable (HTTP {resp.status}): {label} — {url}"
            except urllib.error.URLError as inner_exc:
                return f"Link check failed for {label} ({url}): {inner_exc.reason}"
        else:
            return f"Link not reachable (HTTP {exc.code}): {label} — {url}"
    except urllib.error.URLError as exc:
        return f"Link check failed for {label} ({url}): {exc.reason}"
    return None


def check_links(
    projects: list[dict[str, Any]],
    social: dict[str, Any],
    *,
    offline: bool = False,
    timeout: int = _DEFAULT_TIMEOUT,
) -> list[str]:
    """Validate URLs in *projects* and *social*.

    Args:
        projects: parsed projects.json list (each item may have a ``url`` key).
        social: parsed social.json dict (only http(s) values are checked).
        offline: when True, skip all network requests and return ``[]``.
        timeout: per-request socket timeout in seconds.

    Returns:
        A list of warning strings (empty when everything resolves or the check
        is skipped). Never raises.
    """
    if offline or os.environ.get("SKIP_LINK_CHECK") == "1":
        return []

    warnings: list[str] = []

    for project in projects:
        name = project.get("name", "<unnamed>")
        url = (project.get("url") or "").strip()
        if not url:
            warnings.append(f"Project '{name}' has no URL")
            continue
        warning = _check_url(f"project '{name}'", url, timeout)
        if warning is not None:
            warnings.append(warning)

    for key, value in social.items():
        if isinstance(value, str) and _is_http_url(value):
            warning = _check_url(f"social '{key}'", value, timeout)
            if warning is not None:
                warnings.append(warning)

    return warnings
