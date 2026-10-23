"""Icon reachability helper — stdlib only (urllib), no requests dependency.

``check_icons`` issues a HEAD request (fallback GET on HTTP 405) for each
skillicons slug or ``iconUrl`` entry found in the skills data. Non-200
responses and network errors produce warning strings; the function never
raises. The check is fully skippable via ``SKIP_ICON_CHECK=1`` or the
``offline`` keyword argument.
"""

import os
import urllib.error
import urllib.request
from typing import Any

SKILLICONS_BASE = "https://skillicons.dev/icons?i="
_DEFAULT_TIMEOUT = 5  # seconds


def _resolve_urls(skills: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract (slug_or_name, url) pairs from the skills data structure."""
    pairs: list[tuple[str, str]] = []
    for cat in skills.get("categories", []):
        for entry in cat.get("details", []):
            if isinstance(entry, str):
                continue
            icon_url = entry.get("iconUrl")
            if icon_url:
                pairs.append((entry.get("name", icon_url), icon_url))
                continue
            slug = entry.get("icon")
            if slug:
                pairs.append((slug, f"{SKILLICONS_BASE}{slug}"))
    return pairs


def _check_url(label: str, url: str, timeout: int) -> str | None:
    """Return a warning string if the URL is not reachable; else None.

    Uses HEAD first; falls back to GET on HTTP 405 Method Not Allowed.
    """
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return f"Icon not reachable (HTTP {resp.status}): {label} — {url}"
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            # HEAD not allowed — retry with GET
            get_req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                    if resp.status != 200:
                        return f"Icon not reachable (HTTP {resp.status}): {label} — {url}"
            except urllib.error.URLError as inner_exc:
                return f"Icon check failed for {label} ({url}): {inner_exc.reason}"
        else:
            return f"Icon not reachable (HTTP {exc.code}): {label} — {url}"
    except urllib.error.URLError as exc:
        return f"Icon check failed for {label} ({url}): {exc.reason}"
    return None


def check_icons(
    skills: dict[str, Any], *, offline: bool = False, timeout: int = _DEFAULT_TIMEOUT
) -> list[str]:
    """Check all icon URLs in *skills* for reachability.

    Args:
        skills: parsed skills.json dict (``{"categories": [...]}``).
        offline: when True, skip all network requests and return ``[]``.
        timeout: per-request socket timeout in seconds.

    Returns:
        A list of warning strings (empty when all icons resolve or check
        is skipped). Never raises.
    """
    if offline or os.environ.get("SKIP_ICON_CHECK") == "1":
        return []

    warnings: list[str] = []
    for label, url in _resolve_urls(skills):
        warning = _check_url(label, url, timeout)
        if warning is not None:
            warnings.append(warning)
    return warnings
