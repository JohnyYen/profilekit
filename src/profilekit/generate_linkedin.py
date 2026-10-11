"""Generate a full LinkedIn profile from canonical profile data."""

import sys
from pathlib import Path

from profilekit.context import ProjectContext, discover_project
from profilekit.render import format_date_range
from profilekit.utils import (
    load_json,
    run,
    skill_name,
    what_i_build,
    write_output,
)

MAX_HEADLINE_LENGTH = 220


def truncate_headline(headline: str, max_len: int = MAX_HEADLINE_LENGTH) -> str:
    if len(headline) <= max_len:
        return headline
    truncated = headline[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated


def compute_headline(about: dict) -> str:
    """Return the LinkedIn headline for the given about dict.

    Prefers `linkedinHeadline`; falls back to `headline` then `tagline`.
    When the raw value exceeds MAX_HEADLINE_LENGTH, truncates to word boundary
    and emits a warning to stderr.
    """
    raw = about.get("linkedinHeadline") or about.get("headline", about.get("tagline", ""))
    if len(raw) > MAX_HEADLINE_LENGTH:
        print(
            f"WARNING: linkedinHeadline is {len(raw)} characters, "
            f"which exceeds the LinkedIn 220-character limit. Truncating.",
            file=sys.stderr,
        )
    return truncate_headline(raw)


def render_linkedin_about(about: dict) -> str:
    """Render the About / summary section for LinkedIn."""
    lines = ["## About", "", about.get("description", ""), ""]

    if about.get("currentFocus"):
        lines.append("## Current Focus")
        lines.append("")
        for item in about["currentFocus"]:
            lines.append(f"- **{item['title']}**: {item['description']}")
        lines.append("")

    # "What I build" section — uses platform variant when available
    items = what_i_build(about, "linkedin")
    if items:
        lines.append("## What I Build")
        lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def render_linkedin_experience(experience: list) -> str:
    """Render the Experience section for LinkedIn."""
    lines = ["## Experience", ""]
    for entry in experience:
        date_str = format_date_range(
            entry.get("start_date", ""), entry.get("end_date", ""), default_end="present"
        )
        lines.append(f"**{entry['position']}** at {entry['company']}")
        lines.append(f"{date_str} | {entry.get('location', '')}")
        lines.append("")
        if entry.get("summary"):
            lines.append(entry["summary"])
            lines.append("")
        for h in entry.get("highlights", []):
            lines.append(f"- {h}")
        lines.append("")
    return "\n".join(lines)


def render_linkedin_education(education: list) -> str:
    """Render the Education section for LinkedIn."""
    lines = ["## Education", ""]
    for entry in education:
        date_str = format_date_range(entry.get("start_date", ""), entry.get("end_date", ""))
        lines.append(f"**{entry['degree']} in {entry['area']}**")
        lines.append(f"{entry['institution']} | {date_str}")
        lines.append(f"Location: {entry.get('location', '')}")
        lines.append("")
        for h in entry.get("highlights", []):
            lines.append(f"- {h}")
        lines.append("")
    return "\n".join(lines)


def render_linkedin_skills(skills: dict) -> str:
    """Render the Skills section for LinkedIn."""
    lines = ["## Skills", ""]
    for cat in skills.get("categories", []):
        lines.append(f"**{cat['label']}**: {', '.join(skill_name(e) for e in cat['details'])}")
    lines.append("")
    return "\n".join(lines)


def main(ctx: ProjectContext | None = None, output_dir: Path | None = None) -> None:
    """Compose the LinkedIn copy and write it to linkedin.md.

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
    experience = load_json("experience.json", ctx.data_dir)
    education = load_json("education.json", ctx.data_dir)
    skills = load_json("skills.json", ctx.data_dir)

    headline_section = "\n".join(["## Headline", "", compute_headline(about), ""])
    about_section = render_linkedin_about(about)
    experience_section = render_linkedin_experience(experience)
    education_section = render_linkedin_education(education)
    skills_section = render_linkedin_skills(skills)

    output = "\n".join(
        [
            headline_section,
            about_section,
            experience_section,
            education_section,
            skills_section,
        ]
    )

    output_path = write_output(output, out_dir, "linkedin.md")
    print(f"Generated linkedin.md at {output_path}")


if __name__ == "__main__":
    run(main)
