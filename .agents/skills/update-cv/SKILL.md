---
name: update-cv
description: Update content in Johny's RenderCV YAML and auto-compile to PDF/HTML/PNG
license: Apache-2.0
metadata:
  author: johny
  version: "1.0"
---

## Project Context

- CV source: `Johny_A._Pedraza_Romero_CV.yaml` (RenderCV v2.8 schema)
- Renderer: `.venv/bin/rendercv` (installed via `uv` in the project venv)
- Output dir: `rendercv_output/`
- Theme: `classic`, locale: English
- Compile command: `.venv/bin/rendercv render Johny_A._Pedraza_Romero_CV.yaml`

## YAML Structure

The CV YAML follows this structure:

```yaml
cv:
  name, headline, location, email, phone
  social_networks:
  sections:
    education:
    experience:
    projects:
    startup_projects:  # commented — placeholder for future startup products
    skills:
      - label: <category>
        details: <comma-separated skills>
    # publications: (commented)
  design:
    theme: classic
  locale:
    language: english
  settings:
    current_date: YYYY-MM-DD
```

## Workflow

1. **Ask before writing** — Use the `question` tool in grouped format to ask what the user wants to update. Ask about one section at a time. Suggest improvements when relevant but let the user decide.

2. **Supported sections** — education, experience, projects, startup_projects (commented placeholder), skills, headline, settings.current_date. Respect the existing YAML structure and format.

3. **Skills format** — Each skill is a `label` + `details` pair. Categories: Back-end Frameworks, ERP Platforms, Databases, Dev & Infrastructure, Languages, Software Design, AI-Driven Development. Don't add categories the user hasn't used or explicitly requested.

4. **English only** — The CV and all its content stays in English. No Spanish in the YAML values.

5. **Compile on completion** — After finishing all updates, auto-compile without asking:
   ```
   .venv/bin/rendercv render Johny_A._Pedraza_Romero_CV.yaml
   ```

6. **No over-editing** — Don't reformat the YAML or touch sections the user didn't ask about. Don't "improve" designs or locale unless explicitly requested.

7. **Ask at most one question at a time** per the orchestrator rules. When asking about what to update, use the `question` tool with grouped options.
