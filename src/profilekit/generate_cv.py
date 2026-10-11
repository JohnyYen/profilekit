"""Generate RenderCV-compatible YAML and human-readable markdown CV from canonical profile data."""

from pathlib import Path

from profilekit.context import ProjectContext, discover_project
from profilekit.render import format_education_entry_yaml, format_experience_entry_yaml
from profilekit.utils import (
    load_json,
    run,
    skill_name,
    what_i_build,
    write_output,
)

# RenderCV presentation defaults. These are the author's taste, overridable
# through ``[generators.cv]``. The values reproduce what this project
# published before they were configurable.
DEFAULT_THEME = "classic"
DEFAULT_LOCALE = "english"
DEFAULT_RENDERCV_SCHEMA = "v2.8"

# RenderCV resolves "auto" at render time. The previous value was a frozen
# literal date, which is a determinism trap: it silently aged out, and every
# regeneration kept asserting a date from the past. A project that needs a
# fixed date pins it explicitly — which is what the golden snapshots do.
DEFAULT_CURRENT_DATE = "auto"


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


def main(ctx: ProjectContext | None = None, output_dir: Path | None = None) -> None:
    """Compose the RenderCV YAML and the readable CV, and write both.

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

    options = ctx.generator_options("cv")
    theme = options.get("theme", DEFAULT_THEME)
    locale = options.get("locale", DEFAULT_LOCALE)
    rendercv_schema = options.get("rendercv_schema", DEFAULT_RENDERCV_SCHEMA)
    current_date = options.get("current_date", DEFAULT_CURRENT_DATE)

    about = load_json("about.json", ctx.data_dir)
    experience = load_json("experience.json", ctx.data_dir)
    education = load_json("education.json", ctx.data_dir)
    skills = load_json("skills.json", ctx.data_dir)
    projects = load_json("projects.json", ctx.data_dir)
    social = load_json("social.json", ctx.data_dir)

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
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/"
        f"rendercv/rendercv/refs/tags/{rendercv_schema}/schema.json",
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
            f"  theme: {theme}",
            "  links:",
            "    show_external_link_icon: true",
            "locale:",
            f"  language: {locale}",
            "settings:",
            f'  current_date: "{current_date}"',
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
    write_output(yaml_content, out_dir, "cv.yml")

    md_content = render_cv_markdown(about, experience, education, projects, skills, social)
    write_output(md_content, out_dir, "cv.md")

    print(f"Generated cv.yml and cv.md in {out_dir}")


if __name__ == "__main__":
    run(main)
