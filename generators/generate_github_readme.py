#!/usr/bin/env python3
"""Generate a rich, iconized GitHub profile README from canonical profile data."""

import sys
import warnings
from pathlib import Path

from generators.render import format_date_range
from generators.utils import load_json, load_json_strict, run, what_i_build, write_output, skill_icon, skill_name

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
ASSETS_DIR = ROOT_DIR / "assets"

# Spacer image injected between icons in each row
IMG_SPACER = '<img width="15" />'

SKILLICONS_BASE = "https://skillicons.dev/icons?i="


def render_header(about: dict) -> str:
    """Render the centered HTML header with h1 (username) and h2 (headline/tagline).

    Prefers `githubReadmeSummary` for the h2 subtitle; falls back to
    `headline` then `tagline`.
    """
    name = about.get("username", "")
    subtitle = (
        about.get("githubReadmeSummary")
        or about.get("headline")
        or about.get("tagline", "")
    )
    lines = [
        f'<h1 align="center">Hi 👋, I\'m {name}</h1>',
        f'<h2 align="center"><b>{subtitle}</b></h2>',
        "",
    ]
    return "\n".join(lines)


def render_what_i_build_section(about: dict) -> str:
    """Render the 'What I build' section from whatIBuildVariants[github] or whatIBuild."""
    items = what_i_build(about, "github")
    if not items:
        return ""
    lines = ["### What I build", ""]
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_about_html(about: dict, assets_dir: Path | None = None) -> str:
    """Render the centered about block with the pixel-mario gif.

    Emits the mario gif as a relative path `assets/pixel-mario.gif`.
    Warns to stderr when the asset is missing so regeneration can continue
    even if the gif has not been downloaded yet.
    """
    if assets_dir is None:
        assets_dir = ASSETS_DIR

    mario_path = assets_dir / "pixel-mario.gif"
    if not mario_path.exists():
        print(
            f"WARNING: assets/pixel-mario.gif not found at {mario_path}. "
            "Run the asset download step before regenerating.",
            file=sys.stderr,
        )

    description = about.get("description", "")
    lines = [
        '<div align="center">',
        f'  <img src="assets/pixel-mario.gif" alt="pixel mario" />',
        "</div>",
        "",
        description,
        "",
    ]
    return "\n".join(lines)


def render_focus(about: dict) -> str:
    """Render the 'What I focus on' bullet section from currentFocus entries."""
    items = about.get("currentFocus", [])
    if not items:
        return ""
    lines = ["### What I focus on", ""]
    for item in items:
        lines.append(f"- **{item['title']}**: {item['description']}")
    lines.append("")
    return "\n".join(lines)


def render_icon_rows(skills: dict) -> str:
    """Render per-category icon rows as centered HTML div blocks.

    For each skill category:
    - Entries with an `icon` slug emit: <img src="https://skillicons.dev/icons?i=<slug>" height="60" alt="<name> logo" />
    - Entries with an `iconUrl` emit:   <img src="<iconUrl>" height="60" alt="<name> logo" />
    - `iconUrl` takes priority over `icon` when both are present.
    - Plain-string entries (no icon data) are silently omitted from rows.
    - Categories with zero icon entries are skipped entirely.

    Adjacent icon imgs are separated by IMG_SPACER (`<img width="15" />`).
    """
    output_parts: list[str] = []

    for cat in skills.get("categories", []):
        icon_imgs: list[str] = []
        for entry in cat.get("details", []):
            icon_result = skill_icon(entry)
            if icon_result is None:
                # Plain string — no icon
                continue
            slug, icon_url = icon_result
            if icon_url:
                src = icon_url
            elif slug:
                src = f"{SKILLICONS_BASE}{slug}"
            else:
                # Object but no icon fields — skip
                continue
            name = skill_name(entry)
            icon_imgs.append(
                f'<img src="{src}" height="60" alt="{name} logo" />'
            )

        if not icon_imgs:
            # No icons in this category — skip the entire div
            continue

        label = cat.get("label", "")
        row_content = f"\n  {IMG_SPACER}\n  ".join(icon_imgs)
        output_parts.append(
            f'<h3 align="center">{label}</h3>\n'
            f'<div align="center">\n'
            f"  {row_content}\n"
            f"</div>\n"
        )

    return "\n".join(output_parts)


def render_experience_text(experience: list) -> str:
    """Render a brief text summary of experience entries."""
    if not experience:
        return ""
    lines = ["### Experience", ""]
    for entry in experience:
        date_str = format_date_range(entry.get("start_date", ""), entry.get("end_date", ""), default_end="present")
        lines.append(f"**{entry['position']}** at **{entry['company']}**")
        lines.append(date_str)
        if entry.get("summary"):
            lines.append(entry["summary"])
        lines.append("")
    return "\n".join(lines)


def render_learning(about: dict) -> str:
    """Render the learningJourney text section."""
    journey = about.get("learningJourney", "")
    if not journey:
        return ""
    lines = ["### Currently learning", "", journey, ""]
    return "\n".join(lines)


def render_footer(about: dict) -> str:
    """Render the closing footer with an optional quote and invite."""
    quote = about.get("githubQuote", "")
    lines: list[str] = []
    if quote:
        lines.append(f"> {quote}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Feel free to reach out for collaboration, architecture discussions, or just to say hi!*")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Compose the GitHub profile README and write it to output/github-readme.md."""
    about = load_json("about.json", DATA_DIR)
    skills = load_json("skills.json", DATA_DIR)
    experience = load_json("experience.json", DATA_DIR)

    sections = [
        render_header(about),
        render_what_i_build_section(about),
        render_about_html(about, ASSETS_DIR),
        render_focus(about),
        render_icon_rows(skills),
        render_experience_text(experience),
        render_learning(about),
        render_footer(about),
    ]

    output = "\n".join(s for s in sections if s)
    output_path = write_output(output, OUTPUT_DIR, "github-readme.md")
    print(f"Generated github-readme.md at {output_path}")


if __name__ == "__main__":
    run(main)
