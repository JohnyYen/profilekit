#!/usr/bin/env python3
"""Generate a rich, iconized GitHub profile README from canonical profile data."""

import sys
from pathlib import Path

from profilekit.context import ProjectContext, discover_project
from profilekit.render import format_date_range
from profilekit.utils import (
    load_json,
    run,
    skill_icon,
    skill_name,
    what_i_build,
    write_output,
)

# Spacer image injected between icons in each row
IMG_SPACER = '<img width="15" />'

SKILLICONS_BASE = "https://skillicons.dev/icons?i="


def render_header(about: dict) -> str:
    """Render the centered HTML header with h1 (username) and h2 (headline/tagline).

    Prefers `githubReadmeSummary` for the h2 subtitle; falls back to
    `headline` then `tagline`.
    """
    name = about.get("username", "")
    subtitle = about.get("githubReadmeSummary") or about.get("headline") or about.get("tagline", "")
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


def render_about_html(about: dict, assets_dir: Path) -> str:
    """Render the centered about block with the pixel-mario gif.

    Emits the mario gif as a relative path `assets/pixel-mario.gif`.
    Warns to stderr when the asset is missing so regeneration can continue
    even if the gif has not been downloaded yet.

    ``assets_dir`` is required: the caller owns it, so there is no module
    constant to fall back to.
    """
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
        '  <img src="assets/pixel-mario.gif" alt="pixel mario" />',
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
    - Entries with an `icon` slug emit a skillicons.dev <img> (height 60).
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
            icon_imgs.append(f'<img src="{src}" height="60" alt="{name} logo" />')

        if not icon_imgs:
            # No icons in this category — skip the entire div
            continue

        label = cat.get("label", "")
        row_content = f"\n  {IMG_SPACER}\n  ".join(icon_imgs)
        output_parts.append(
            f'<h3 align="center">{label}</h3>\n<div align="center">\n  {row_content}\n</div>\n'
        )

    return "\n".join(output_parts)


def render_experience_text(experience: list) -> str:
    """Render a brief text summary of experience entries."""
    if not experience:
        return ""
    lines = ["### Experience", ""]
    for entry in experience:
        date_str = format_date_range(
            entry.get("start_date", ""), entry.get("end_date", ""), default_end="present"
        )
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
    lines.append(
        "*Feel free to reach out for collaboration, architecture discussions, or just to say hi!*"
    )
    lines.append("")
    return "\n".join(lines)


def main(ctx: ProjectContext | None = None, output_dir: Path | None = None) -> None:
    """Compose the GitHub profile README and write it to github-readme.md.

    ``ctx`` carries the project's resolved directories. Passing ``None``
    discovers the project from the working directory, which is what the CLI
    does; tests construct a context over a temporary directory instead of
    monkeypatching module globals.

    ``output_dir`` overrides the context's output directory. A generator
    writes only where it was told, which is what keeps it a generator and
    not a publisher.
    """
    ctx = ctx or discover_project()
    out_dir = output_dir or ctx.output_dir

    about = load_json("about.json", ctx.data_dir)
    skills = load_json("skills.json", ctx.data_dir)
    experience = load_json("experience.json", ctx.data_dir)

    sections = [
        render_header(about),
        render_what_i_build_section(about),
        render_about_html(about, ctx.assets_dir),
        render_focus(about),
        render_icon_rows(skills),
        render_experience_text(experience),
        render_learning(about),
        render_footer(about),
    ]

    output = "\n".join(s for s in sections if s)
    output_path = write_output(output, out_dir, "github-readme.md")
    print(f"Generated github-readme.md at {output_path}")


if __name__ == "__main__":
    run(main)
