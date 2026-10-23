# Contributing

Thanks for considering a contribution. This project is a small, opinionated
tool: structured profile data in, generated artifacts out, with an optional
publication layer for pushing those artifacts to real destinations.

## Quick path

1. Fork and clone the repository.
2. `uv sync --extra dev` — installs runtime + dev dependencies into `.venv`.
3. Make your change, with tests. This project runs in **strict TDD**: write
   the failing test first, then the minimal code that makes it pass.
4. `uv run pytest -q` — the full suite must stay green with coverage at or
   above the configured gate (`--cov-fail-under` in `pyproject.toml`).
5. `uv run ruff check . && uv run ruff format --check .` and `uv run mypy` —
   lint, format, and type-check must pass.
6. Open a pull request describing the behavior change, not the file list.

## Development setup

```sh
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
pre-commit install   # optional, runs the same checks before each commit
```

## Code organization

- `src/profilekit/` — the installable package: generators, validation, and
  the `profile` CLI.
- `data/` — this repository's own canonical profile data (not shipped with
  the package; it's the project's own dogfood input).
- `tests/` — the pytest suite, including golden/snapshot tests under
  `tests/golden/`.
- `docs/` — contributor-facing reference material (data contract, authoring
  guides for generators/publishers).

### All file writes go through `profilekit.safe_io`

Never call `write_text`, `write_bytes`, `open(..., "w")`, `os.replace`,
`shutil` copies, or similar directly in `src/profilekit`. Use
`profilekit.safe_io.write_file(path, data, root=..., overwrite=...)`: it
refuses symlinks, paths outside `root`, and unrequested overwrites, writes
bytes, and replaces files atomically. `tests/test_architecture_writes.py`
fails on any direct write elsewhere, naming the module and line.

## Commit and PR conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit
  messages (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Keep pull requests focused on one deliverable change. Large or structural
  changes are easier to review split into smaller, self-contained commits.
- Every behavioral change needs a test. Mechanical, zero-behavior-change
  moves (e.g. file relocations) do not need an invented test, but anything
  that changes an import path, entry point, or packaging behavior does.

## Reporting bugs or requesting features

Open a GitHub issue with a clear description, reproduction steps (for bugs),
and expected vs. actual behavior.

## Security issues

Do not open a public issue for security vulnerabilities — see `SECURITY.md`
for the private reporting process.

## Code of Conduct

By participating in this project, you agree to abide by `CODE_OF_CONDUCT.md`.
