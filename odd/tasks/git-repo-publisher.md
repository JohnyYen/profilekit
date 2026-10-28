# git-repo publisher: deliver generated artifacts to another repository

Locator: `odd/tasks/git-repo-publisher.md` · Engram mirror: `odd/git-repo-publisher/tasks`

## Objective
Add a `git-repo` publisher kind so `profile publish --execute` commits and pushes generated
artifacts straight into the repositories that serve them (profile README, CV repo, portfolio),
instead of the owner cloning, copying, committing and pushing each one by hand.

## Problem / why
On 2026-10-28 refreshing the owner's profiles took three manual clones and pushes
(`JohnyYen/JohnyYen`, `JohnyYen/my-cv`, `JohnyYen/my-portfolio-terminal`). The only push
publisher, `filesystem`, writes inside this project. The hand-written README sections were
also overwritten silently, because nothing compared the destination with what was last published.

## Scope
- New publisher kind `git-repo` (capability `push`, `reads_destination = true`).
- Config per destination in `profile.toml`:
  `repo` (`owner/name` or any git URL), `branch` (default `main`),
  `files` (destination path -> source path; a source resolves against the output dir first,
  then the project root, e.g. `assets/pixel-mario.gif`), `message` (commit message, has a default),
  `on_conflict` (`refuse` default | `overwrite`).
- Plan clones shallowly into a temp dir and computes changed files; dry run shows them and writes nothing.
- Publish commits only changed files and pushes; no empty commits; a push failure is this
  destination's `failed`, never a fake `published`.
- Credentials come from the user's existing git/gh setup; no token in config.
- Manual-edit guard: if a destination file differs from both the new content and the digest
  this tool last published (ledger), the plan flags a conflict and publish refuses
  unless `on_conflict = "overwrite"`.

## Out of scope
- Configuring and executing the owner's real destinations (owner decides after merge).
- `profile audit` (live drift report) — a later feature.
- Push, PR and merge of this branch stay with the owner.

## Constraints
- Python, mypy strict, ruff (BLE, S, TRY), pre-commit; every file write through `safe_io`.
- Git is driven through the `git` CLI via `subprocess` with argument lists (no shell).
- Tests use a local bare repository as the remote (`file://`), never the network.
- RDD is OFF for this clone (`gentle-ai review mode status`: clone_local off); ordinary checks only.
- Delivery strategy: `ask-on-risk`. Forecast ~600-800 authored lines incl. tests -> ask the owner
  for a chain strategy before opening a PR; work-unit commits on `feat/git-repo-publisher`.

## Tasks (route: delegated — one writer, 2+ non-trivial files across src, tests, docs)
- [x] G1 Config parsing + plan: `GitRepoPublisher.plan` validates config (config errors are
      clear `failed`), clones the remote shallowly, maps `files`, computes `changes`. Test-first
      against a local bare repo fixture. Commit.
- [x] G2 Publish: write changed files in the clone, commit with `message`, push to `branch`;
      `unchanged` when nothing differs; push/clone errors become `failed` with detail. Test-first. Commit.
- [x] G3 Wiring: entry point `git-repo` in `pyproject.toml`, kind mapping in `publish._load_publisher`
      (native capability + staleness), dry-run output lists changed files. Test-first. Commit.
- [x] G4 Manual-edit guard using the publish ledger + `on_conflict`. Test-first. Commit.
- [x] G5 Docs: `docs/authoring-publishers.md`, README publishing section, commented `profile.toml`
      example for the three owner repos. Commit.
- [x] G6 Normalisation-aware comparison: compare and record the blob git commits (`.gitattributes`
      eol/filters), so the guard never false-conflicts and a dry run never promises a change git
      normalises away. Test-first. Commit.
- [x] G7 Credentials in `repo`: reject http(s) userinfo at config parse; redact userinfo in
      every detail. Test-first. Commit.
- [ ] G8 Owner layouts in the commented `profile.toml`; document that an empty remote or a
      missing branch is unsupported. Commit.

## Acceptance criteria
- Dry run against a bare-repo fixture lists exactly the files that would change and writes nothing.
- `--execute` produces one commit on the remote branch with only changed files; a second run is `unchanged`.
- A hand-edited destination file blocks the publish with a clear detail unless `on_conflict = "overwrite"`.
- Full suite, mypy strict, ruff and pre-commit green; coverage stays >= 80%.

## Checks
`uv run --extra dev pytest -q`, `uv run --extra dev mypy`, `uv run --extra dev ruff check .`,
`uv run --extra dev ruff format --check .`, `uv run profilekit --offline check`.

## Progress
- 2026-10-28 Branch `feat/git-repo-publisher` created from `main` (`73cc0f5`). Feature document created.
- G1 `c2a5a16` (route: delegated writer). RED: `pytest tests/test_publisher_git_repo.py` ->
  `ModuleNotFoundError: profilekit.publishers.git_repo`. GREEN: 31 passed. `Artifact` gained an
  optional `data: bytes` + `encoded()` so binary sources (gif) publish byte-for-byte; `plan_digest`
  hashes `encoded()` (identical digest for text). Full suite 749 passed; mypy, ruff green.
  Decision: the publisher inherits the environment untouched (no scrubbing of `GIT_DIR` etc.),
  because `tests/test_secrets.py` forbids publishers reading the environment.
- G2 (see commit below). RED: 9 failed with `AttributeError: publish`. GREEN: 42 passed.
  `publish()` re-clones, refuses if the branch moved since the plan (`remote_digest` = planned
  HEAD), writes via `safe_io.write_file`, no empty commits, push errors -> `failed` with git's
  stderr. Identity: user's own when `git var GIT_AUTHOR_IDENT`/`GIT_COMMITTER_IDENT` resolve,
  else fallback `profilekit <profilekit@localhost>`.
- G2 commit `73c524c`.
- G3 (see commit below). RED: 5 failed (`git-repo` not registered; CLI rows `failed` with
  `unknown kind`). GREEN: 47 passed; full suite 765 passed. Entry point `git-repo` in
  `pyproject.toml`, mapped to `GitRepoPublisher` in `publish._native_publishers`; dry run row
  reads `would-publish  dry run — would write: README.md, docs/cv.md`.
- G3 commit `d09bdb5`.
- G4 (see commit below). RED: 4 failed (no conflict detection, no `publish.ledger_key`).
  GREEN: 53 passed; full suite 771 passed, coverage 97.30%; mypy, ruff green. Design: the guard
  lives in the core (`publish.manual_edits`), which owns the ledger. `PublishPlan` gained
  `destination_digests` (opt-in, per-file SHA-256 of what the destination holds, `None` = absent)
  and `on_conflict`; per-file ledger entries use `"<destination>::<path>"`. A verified-equal file
  is recorded as a baseline; changed files are recorded after `published`. Decisions: a file that
  exists but was never published by profilekit counts as edited (the hand-written README case);
  a conflict is `failed` on the dry run too, so the table never promises a write `--execute`
  refuses. G3 CLI tests now opt in with `on_conflict = "overwrite"` because their seeded README
  is hand-written.
- G4 commit `7a2940e`.
- G5 `6793ba4`. Passive docs: structural checks only (no meaningful RED). README
  publishing section documents `git-repo` (config, dry run, credentials, conflict guard);
  `docs/authoring-publishers.md` documents `Artifact.data` and the opt-in guard; `profile.toml`
  holds the three owner repositories commented out. `tests/test_docs_coherence.py` accepts
  `git-repo` as a shipped kind in TOML examples. Final checks: pytest 771 passed (97.30%),
  mypy strict clean, ruff check/format clean, `profilekit --offline check` passed,
  `profilekit publish` dry run shows only `portfolio-data` and `linkedin`.
- Follow-up: `pre-commit run --all-files` found that the pinned mypy hook does not narrow
  `on_conflict` through `!=`; fixed with explicit narrowing (`fix(publish)` commit). All hooks pass.

- G6 (verifier finding). RED: 3 failed against a remote with `* text=auto eol=lf` and a CRLF
  source — plan reported `README.md` changed, the second `--execute` failed with a false
  `conflict`, and the overwrite dry run said `would-publish`. GREEN: 56 passed; suite 774 passed.
  Fix: `committed_form()` runs `git hash-object -w --path <dest> --stdin` in the temporary clone
  and compares that blob with the remote blob; `PublishPlan.published_digests` carries the
  committed digest so the core ledger records it instead of the source bytes.
- G7 (verifier finding). RED: 10 failed (`check_repo`/`redact` missing; credentialed http(s)
  URLs accepted; git stderr passed through unredacted). GREEN: 66 passed. `check_repo` refuses
  http(s) userinfo with a config error pointing to a credential helper / `gh auth login`;
  scp-style and `ssh://git@` URLs still accepted. `redact()` scrubs userinfo in git stderr, clone
  errors and every result detail. The git-error test fakes `subprocess.run` (no network).

## Next step
Owner: review the commented destinations in `profile.toml` (paths per repository layout), decide
the chain strategy before opening a PR (forecast exceeded ~400 lines), then push/PR.
