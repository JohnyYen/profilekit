# Security Policy

This policy covers the **`profilekit`** package (import package
`profilekit`, distributed from this repository).

## Supported Versions

This project is pre-1.0. Only the latest released version on PyPI receives
security fixes.

## Reporting a Vulnerability

Please report security vulnerabilities privately — do not open a public
GitHub issue.

Email: **johny.antonio.pedraza.romero@gmail.com**

Include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce (a minimal repro project is ideal).
- The affected version(s).

You should receive an initial response within 5 business days. Once a fix is
available, it will be released and the reporter credited (unless anonymity is
requested).

## Non-Goals

This project is **not** a secret store and does not integrate with any vault
backend. Credentials passed to publishers are resolved per-invocation from
environment variables declared in `profile.toml` and are never persisted by
this tool. See `design.md` (decision D1) in
`openspec/changes/2026-09-09-open-source-release/` for the full threat model
behind the publication layer.
