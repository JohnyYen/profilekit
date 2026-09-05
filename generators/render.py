"""Shared pure formatting helpers for profile data generators.

All functions in this module are pure (no I/O, no side effects). They
extract formatting logic that was previously duplicated across
``generate_cv.py``, ``generate_linkedin.py``, and ``generate_github_readme.py``.

Callers import the functions they need; no generator is forced to use all of
them.
"""


# ---------------------------------------------------------------------------
# Internal helper shared by YAML formatters
# ---------------------------------------------------------------------------


def _escape_yaml_string(value: str) -> str:
    """Escape a string for safe YAML embedding (mirrors generate_cv.escape_yaml_string)."""
    if "\n" in value:
        return f"|-\n{value}"
    if any(
        c in value
        for c in [
            ":",
            "#",
            "{",
            "}",
            "[",
            "]",
            "&",
            "*",
            "?",
            "|",
            "-",
            "<",
            ">",
            "=",
            "!",
            "%",
            "@",
            "`",
        ]
    ):
        return f'"{value}"'
    return value


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------


def format_date_range(start: str, end: str, *, default_end: str = "Present") -> str:
    """Return a formatted date range string.

    Args:
        start: start date string (e.g. "2020").
        end: end date string; when empty or falsy, *default_end* is used.
        default_end: string to use when *end* is absent (default: "Present").

    Returns:
        ``"<start> – <end>"`` with the em-dash separator.
    """
    end_display = end if end else default_end
    return f"{start} – {end_display}"


# ---------------------------------------------------------------------------
# YAML entry formatters (used by generate_cv.py)
# ---------------------------------------------------------------------------


def format_experience_entry_yaml(entry: dict) -> str:
    """Render a single experience entry as an indented YAML block.

    Matches the format expected by RenderCV (8-space block indent, 10-space
    highlights indent). Output is identical to the legacy inline formatter in
    ``generate_cv.py``.
    """
    lines = [
        f"      - company: {_escape_yaml_string(entry['company'])}",
        f"        position: {_escape_yaml_string(entry['position'])}",
        "        date:",
        f"        start_date: {entry.get('start_date', '')}",
        f"        end_date: {entry.get('end_date', '')}",
        f"        location: {_escape_yaml_string(entry.get('location', ''))}",
        f"        summary: {_escape_yaml_string(entry.get('summary', ''))}",
        "        highlights:",
    ]
    for h in entry.get("highlights", []):
        lines.append(f'          - "{h}"')
    return "\n".join(lines)


def format_education_entry_yaml(entry: dict) -> str:
    """Render a single education entry as an indented YAML block.

    Output is identical to the legacy inline formatter in ``generate_cv.py``.
    """
    lines = [
        f"      - institution: {_escape_yaml_string(entry['institution'])}",
        f"        area: {_escape_yaml_string(entry['area'])}",
        f"        degree: {_escape_yaml_string(entry['degree'])}",
        "        date:",
        f"        start_date: {entry.get('start_date', '')}",
        f"        end_date: {entry.get('end_date', '')}",
        f"        location: {_escape_yaml_string(entry.get('location', ''))}",
        f"        summary: {_escape_yaml_string(entry.get('summary', ''))}",
        "        highlights:",
    ]
    for h in entry.get("highlights", []):
        lines.append(f'          - "{h}"')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown entry formatters (used by generate_linkedin.py, generate_github_readme.py)
# ---------------------------------------------------------------------------


def format_experience_entry_md(entry: dict) -> str:
    """Render a single experience entry as a markdown block.

    Format::

        **<position>** at **<company>**
        <start_date> – <end_date>

        <summary>

        - <highlight 1>
        - ...

    Returns the block as a string (without a trailing blank line).
    """
    end_date = entry.get("end_date", "")
    date_str = format_date_range(entry.get("start_date", ""), end_date, default_end="present")
    lines = [
        f"**{entry['position']}** at **{entry['company']}**",
        date_str,
    ]
    if entry.get("summary"):
        lines.append("")
        lines.append(entry["summary"])
    for h in entry.get("highlights", []):
        lines.append(f"- {h}")
    return "\n".join(lines)


def format_education_entry_md(entry: dict) -> str:
    """Render a single education entry as a markdown block.

    Format::

        **<degree> in <area>**
        <institution> | <start_date> – <end_date>

        - <highlight 1>
        - ...

    Returns the block as a string.
    """
    end_date = entry.get("end_date", "")
    date_str = format_date_range(entry.get("start_date", ""), end_date, default_end="present")
    lines = [
        f"**{entry['degree']} in {entry['area']}**",
        f"{entry['institution']} | {date_str}",
    ]
    for h in entry.get("highlights", []):
        lines.append(f"- {h}")
    return "\n".join(lines)
