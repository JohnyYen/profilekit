"""Generate a rich, iconized GitHub profile README from canonical profile data."""

import sys
from pathlib import Path
from typing import Any

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

# Author-facing defaults. These are taste, not behavior, so each is
# overridable through ``[generators.github-readme]`` in profile.toml. The
# values below reproduce the output this project published before they were
# configurable, so an unset option changes nothing.
DEFAULT_GREETING = "Hi 👋, I'm {name}"
DEFAULT_ABOUT_IMAGE = "assets/pixel-mario.gif"
DEFAULT_FOOTER = (
    "Feel free to reach out for collaboration, architecture discussions, or just to say hi!"
)

SKILLICONS_BASE = "https://skillicons.dev/icons?i="


def render_header(about: dict[str, Any], greeting: str = DEFAULT_GREETING) -> str:
    """Render the centered HTML header with h1 (username) and h2 (headline/tagline).

    Prefers `githubReadmeSummary` for the h2 subtitle; falls back to
    `headline` then `tagline`.
    """
    name = about.get("username", "")
    subtitle = about.get("githubReadmeSummary") or about.get("headline") or about.get("tagline", "")
    lines = [
        f'<h1 align="center">{greeting.format(name=name)}</h1>',
        f'<h2 align="center"><b>{subtitle}</b></h2>',
        "",
    ]
    return "\n".join(lines)


def render_what_i_build_section(about: dict[str, Any]) -> str:
    """Render the 'What I build' section from whatIBuildVariants[github] or whatIBuild."""
    items = what_i_build(about, "github")
    if not items:
        return ""
    lines = ["### What I build", ""]
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_about_html(
    about: dict[str, Any], assets_dir: Path, about_image: str = DEFAULT_ABOUT_IMAGE
) -> str:
    """Render the centered about block, optionally with a decorative image.

    ``about_image`` is a project-relative path. An empty string omits the
    image entirely — a decoration the author likes must be removable by
    everyone else, not merely swappable.

    Warns to stderr when a configured image is missing so regeneration can
    continue rather than failing on an asset that has not been fetched yet.

    ``assets_dir`` is required: the caller owns it, so there is no module
    constant to fall back to.
    """
    description = about.get("description", "")
    if not about_image:
        return "\n".join([description, ""])

    image_path = assets_dir / Path(about_image).name
    if not image_path.exists():
        print(
            f"WARNING: {about_image} not found at {image_path}. Add the asset before regenerating.",
            file=sys.stderr,
        )

    alt = Path(about_image).stem.replace("-", " ")
    lines = [
        '<div align="center">',
        f'  <img src="{about_image}" alt="{alt}" />',
        "</div>",
        "",
        description,
        "",
    ]
    return "\n".join(lines)


def render_focus(about: dict[str, Any]) -> str:
    """Render the 'What I focus on' bullet section from currentFocus entries."""
    items = about.get("currentFocus", [])
    if not items:
        return ""
    lines = ["### What I focus on", ""]
    for item in items:
        lines.append(f"- **{item['title']}**: {item['description']}")
    lines.append("")
    return "\n".join(lines)


def render_icon_rows(skills: dict[str, Any]) -> str:
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


def render_experience_text(experience: list[dict[str, Any]]) -> str:
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


def render_learning(about: dict[str, Any]) -> str:
    """Render the learningJourney text section."""
    journey = about.get("learningJourney", "")
    if not journey:
        return ""
    lines = ["### Currently learning", "", journey, ""]
    return "\n".join(lines)


def render_footer(about: dict[str, Any], footer: str = DEFAULT_FOOTER) -> str:
    """Render the closing footer with an optional quote and sign-off."""
    quote = about.get("githubQuote", "")
    lines: list[str] = []
    if quote:
        lines.append(f"> {quote}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*{footer}*")
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

    options = ctx.generator_options("github-readme")
    greeting = options.get("greeting", DEFAULT_GREETING)
    about_image = options.get("about_image", DEFAULT_ABOUT_IMAGE)
    footer = options.get("footer", DEFAULT_FOOTER)

    sections = [
        render_header(about, greeting),
        render_what_i_build_section(about),
        render_about_html(about, ctx.assets_dir, about_image),
        render_focus(about),
        render_icon_rows(skills),
        render_experience_text(experience),
        render_learning(about),
        render_footer(about, footer),
    ]

    output = "\n".join(s for s in sections if s)
    output_path = write_output(output, out_dir, "github-readme.md")
    print(f"Generated github-readme.md at {output_path}")


if __name__ == "__main__":
    run(main)
