#!/usr/bin/env python3
"""Generate RenderCV-compatible YAML and human-readable markdown CV from canonical profile data."""

from pathlib import Path

from profilekit.render import format_education_entry_yaml, format_experience_entry_yaml
from profilekit.utils import (
    load_json,
    run,
    skill_name,
    what_i_build,
    write_output,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"


def escape_yaml_string(value: str) -> str:
    """Escape a string for safe YAML embedding."""
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


def compute_cv_headline(about: dict) -> str:
    """Return the YAML-escaped CV headline for the given about dict.

    Prefers `cvHeadline`; falls back to `headline` then `tagline`.
    """
    raw = about.get("cvHeadline") or about.get("headline", about.get("tagline", ""))
    return escape_yaml_string(raw)


def format_highlights(highlights: list[str]) -> str:
    lines = []
    for h in highlights:
        lines.append(f'          - "{h}"')
    return "\n".join(lines)


# format_experience_entry and format_education_entry are provided by
# profilekit.render — imported above as format_experience_entry_yaml /
# format_education_entry_yaml.  Local aliases keep call sites unchanged.
format_experience_entry = format_experience_entry_yaml
format_education_entry = format_education_entry_yaml


def format_project_entry(entry: dict) -> str:
    lines = [
        f'      - name: "{entry["name"]}"',
        "        date:",
        f"        start_date: {entry.get('start_date', '')}",
        f"        end_date: {entry.get('end_date', '')}",
        "        location:",
        f"        summary: {escape_yaml_string(entry.get('description', ''))}",
        "        highlights:",
    ]
    for h in entry.get("highlights", []):
        lines.append(f'          - "{h}"')
    return "\n".join(lines)


def format_skill_entry(cat: dict) -> str:
    details = ", ".join(skill_name(e) for e in cat["details"])
    return f"      - label: {cat['label']}\n        details: {details}"


def render_cv_markdown(
    about: dict,
    experience: list,
    education: list,
    projects: list,
    skills: dict,
    social: dict,
) -> str:
    """Render a human-readable markdown CV."""
    headline_text = about.get("cvHeadline") or about.get("headline", about.get("tagline", ""))
    lines = [
        f"# {about.get('username', '')}",
        "",
        f"**{headline_text}**",
        "",
        about.get("description", ""),
        "",
    ]

    # "What I build" section — uses platform variant when available
    cv_build_items = what_i_build(about, "cv")
    if cv_build_items:
        lines.append("## What I Build")
        lines.append("")
        for item in cv_build_items:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Experience")
    lines.append("")
    for entry in experience:
        end_date = entry.get("end_date", "present")
        lines.append(f"### {entry['company']} — {entry['position']}")
        lines.append(f"**{entry.get('start_date', '')} – {end_date}**")
        lines.append("")
        if entry.get("summary"):
            lines.append(entry["summary"])
            lines.append("")
        for h in entry.get("highlights", []):
            lines.append(f"- {h}")
        if entry.get("highlights"):
            lines.append("")

    lines.append("## Education")
    lines.append("")
    for entry in education:
        lines.append(f"### {entry['institution']}")
        lines.append(
            f"**{entry['degree']} in {entry['area']}** | "
            f"{entry.get('start_date', '')} – {entry.get('end_date', '')}"
        )
        lines.append("")
        for h in entry.get("highlights", []):
            lines.append(f"- {h}")
        if entry.get("highlights"):
            lines.append("")

    lines.append("## Skills")
    lines.append("")
    for cat in skills.get("categories", []):
        lines.append(f"**{cat['label']}**: {', '.join(skill_name(e) for e in cat['details'])}")
    lines.append("")

    return "\n".join(lines)


def main():
    about = load_json("about.json", DATA_DIR)
    experience = load_json("experience.json", DATA_DIR)
    education = load_json("education.json", DATA_DIR)
    skills = load_json("skills.json", DATA_DIR)
    projects = load_json("projects.json", DATA_DIR)
    social = load_json("social.json", DATA_DIR)

    # Build social_networks section
    social_networks_lines = []
    if social.get("github"):
        social_networks_lines.append(f"    - network: GitHub\n      username: {social['github']}")
    if social.get("linkedin"):
        social_networks_lines.append(
            f"    - network: LinkedIn\n      username: {social['linkedin']}"
        )

    # Build the YAML
    yaml_lines = [
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/rendercv/rendercv/refs/tags/v2.8/schema.json",
        "cv:",
        f"  name: {escape_yaml_string(about['username'])}",
        f"  headline: {compute_cv_headline(about)}",
        f"  location: {escape_yaml_string(about.get('location', ''))}",
        f"  email: {about.get('email', social.get('email', ''))}",
        f"  phone: {escape_yaml_string(about.get('phone', ''))}",
        "  social_networks:",
    ]
    for line in social_networks_lines:
        yaml_lines.append(line)

    yaml_lines.extend(
        [
            "  custom_connections:",
            "  sections:",
            "    education:",
        ]
    )
    for entry in education:
        yaml_lines.append(format_education_entry(entry))

    yaml_lines.append("    experience:")
    for entry in experience:
        yaml_lines.append(format_experience_entry(entry))

    yaml_lines.append("    projects:")
    for entry in projects:
        yaml_lines.append(format_project_entry(entry))

    yaml_lines.append("    skills:")
    for cat in skills.get("categories", []):
        yaml_lines.append(format_skill_entry(cat))

    yaml_lines.extend(
        [
            "design:",
            "  theme: classic",
            "  links:",
            "    show_external_link_icon: true",
            "locale:",
            "  language: english",
            "settings:",
            '  current_date: "2026-07-30"',
            "  render_command:",
            "    design:",
            "    locale:",
            "    typst_path: rendercv_output/NAME_IN_SNAKE_CASE_CV.typ",
            "    pdf_path: rendercv_output/NAME_IN_SNAKE_CASE_CV.pdf",
            "    markdown_path: rendercv_output/NAME_IN_SNAKE_CASE_CV.md",
            "    html_path: rendercv_output/NAME_IN_SNAKE_CASE_CV.html",
            "    png_path: rendercv_output/NAME_IN_SNAKE_CASE_CV.png",
            "    dont_generate_markdown: false",
            "    dont_generate_html: false",
            "    dont_generate_typst: false",
            "    dont_generate_pdf: false",
            "    dont_generate_png: false",
            "  bold_keywords: []",
        ]
    )

    yaml_content = "\n".join(yaml_lines) + "\n"
    write_output(yaml_content, OUTPUT_DIR, "cv.yml")

    md_content = render_cv_markdown(about, experience, education, projects, skills, social)
    write_output(md_content, OUTPUT_DIR, "cv.md")

    print(f"Generated cv.yml and cv.md in {OUTPUT_DIR}")


if __name__ == "__main__":
    run(main)
