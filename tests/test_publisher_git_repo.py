"""The ``git-repo`` publisher: generated artifacts into another repository.

Every test drives a real ``git`` against a local bare repository standing in
for the remote, reached through a ``file://`` URL. Nothing here touches the
network, and the user's own git configuration is isolated away so a global
setting (commit signing, a hook path, an identity) cannot change the outcome.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from profilekit.context import ProjectContext
from profilekit.publishers.git_repo import (
    GitCommandError,
    GitRepoConfigError,
    GitRepoPlan,
    GitRepoPublisher,
    resolve_repo,
)

GIF_BYTES = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04"


@pytest.fixture(autouse=True)
def _isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point git at an empty global config and give it a test identity."""
    global_config = tmp_path / "gitconfig"
    global_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test Author")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "author@example.com")
    # A test run from a git hook inherits these; they would redirect every
    # git call below into the repository under test.
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(variable, raising=False)


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def make_remote(tmp_path: Path, files: dict[str, bytes], branch: str = "main") -> Path:
    """Create a bare repository whose *branch* holds *files* in one commit."""
    bare = tmp_path / "remote.git"
    _git("init", "--bare", "--initial-branch", branch, str(bare))
    seed = tmp_path / "seed"
    _git("clone", str(bare), str(seed))
    for name, content in files.items():
        path = seed / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    _git("add", "--all", cwd=seed)
    _git("commit", "--message", "initial", cwd=seed)
    _git("push", "origin", f"HEAD:refs/heads/{branch}", cwd=seed)
    return bare


def remote_head(bare: Path, branch: str = "main") -> str:
    return _git("--git-dir", str(bare), "rev-parse", f"refs/heads/{branch}")


def remote_file(bare: Path, path: str, branch: str = "main") -> bytes:
    return subprocess.run(
        ["git", "--git-dir", str(bare), "show", f"{branch}:{path}"],
        capture_output=True,
        check=True,
    ).stdout


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return make_remote(
        tmp_path,
        {"README.md": b"# hand-written\n", "same.txt": b"already current\n"},
    )


@pytest.fixture
def ctx(tmp_path: Path) -> ProjectContext:
    root = tmp_path / "project"
    output = root / "output"
    output.mkdir(parents=True)
    (output / "README.md").write_text("# generated\n", encoding="utf-8")
    (output / "same.txt").write_text("already current\n", encoding="utf-8")
    (output / "cv.md").write_text("# cv\n", encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "pic.gif").write_bytes(GIF_BYTES)
    return ProjectContext.for_root(root)


def _cfg(remote: Path, **overrides: object) -> dict[str, object]:
    cfg: dict[str, object] = {
        "kind": "git-repo",
        "repo": remote.as_uri(),
        "files": {"README.md": "README.md", "same.txt": "same.txt", "docs/cv.md": "cv.md"},
    }
    cfg.update(overrides)
    return cfg


def _project_files(ctx: ProjectContext) -> list[Path]:
    return sorted(p for p in ctx.root.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------
# G1: configuration and plan
# ---------------------------------------------------------------------------


def test_plan_lists_exactly_the_files_that_would_change(ctx: ProjectContext, remote: Path) -> None:
    head = remote_head(remote)
    before = _project_files(ctx)

    plan = GitRepoPublisher().plan(ctx, _cfg(remote))

    assert isinstance(plan, GitRepoPlan)
    assert list(plan.changes) == ["README.md", "docs/cv.md"]
    assert [a.name for a in plan.artifacts] == ["README.md", "same.txt", "docs/cv.md"]
    assert plan.capability == "push"
    assert plan.remote_digest == head
    # Planning writes nothing: not to the remote, not to the project.
    assert remote_head(remote) == head
    assert _project_files(ctx) == before


def test_plan_defaults(ctx: ProjectContext, remote: Path) -> None:
    plan = GitRepoPublisher().plan(ctx, _cfg(remote))
    assert isinstance(plan, GitRepoPlan)
    assert plan.branch == "main"
    assert plan.on_conflict == "refuse"
    assert plan.message


def test_a_source_falls_back_to_the_project_root(ctx: ProjectContext, remote: Path) -> None:
    cfg = _cfg(remote, files={"assets/pic.gif": "assets/pic.gif"})
    plan = GitRepoPublisher().plan(ctx, cfg)

    (artifact,) = plan.artifacts
    assert artifact.encoded() == GIF_BYTES
    assert list(plan.changes) == ["assets/pic.gif"]


def test_the_output_dir_wins_over_the_project_root(ctx: ProjectContext, remote: Path) -> None:
    (ctx.root / "cv.md").write_text("# root copy\n", encoding="utf-8")
    plan = GitRepoPublisher().plan(ctx, _cfg(remote, files={"cv.md": "cv.md"}))
    assert plan.artifacts[0].encoded() == b"# cv\n"


def test_plan_reads_a_configured_branch(ctx: ProjectContext, tmp_path: Path) -> None:
    bare = make_remote(tmp_path, {"README.md": b"# generated\n"}, branch="pages")
    plan = GitRepoPublisher().plan(
        ctx, _cfg(bare, branch="pages", files={"README.md": "README.md"})
    )
    assert list(plan.changes) == []


def test_a_missing_branch_is_a_git_error_naming_it(ctx: ProjectContext, remote: Path) -> None:
    with pytest.raises(GitCommandError, match="no-such-branch"):
        GitRepoPublisher().plan(ctx, _cfg(remote, branch="no-such-branch"))


def test_an_unreachable_repository_is_a_git_error(ctx: ProjectContext, tmp_path: Path) -> None:
    with pytest.raises(GitCommandError, match="clone"):
        GitRepoPublisher().plan(ctx, _cfg(tmp_path / "missing.git"))


@pytest.mark.parametrize(
    ("repo", "expected"),
    [
        ("owner/name", "https://github.com/owner/name.git"),
        ("some-org/repo.name", "https://github.com/some-org/repo.name.git"),
        ("https://example.com/a/b.git", "https://example.com/a/b.git"),
        ("git@example.com:a/b.git", "git@example.com:a/b.git"),
        ("file:///srv/git/b.git", "file:///srv/git/b.git"),
    ],
)
def test_resolve_repo(repo: str, expected: str) -> None:
    assert resolve_repo(repo) == expected


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"repo": None}, "repo"),
        ({"repo": ""}, "repo"),
        ({"repo": "-uhoh"}, "repo"),
        ({"files": None}, "files"),
        ({"files": {}}, "files"),
        ({"files": ["README.md"]}, "files"),
        ({"files": {"README.md": 3}}, "README.md"),
        ({"files": {"/etc/passwd": "README.md"}}, "relative"),
        ({"files": {"../escape.md": "README.md"}}, "escape.md"),
        ({"files": {".git/config": "README.md"}}, ".git"),
        ({"files": {"a\\b.md": "README.md"}}, "backslash"),
        ({"files": {"README.md": "missing.md"}}, "missing.md"),
        ({"files": {"README.md": "/etc/hostname"}}, "relative"),
        ({"files": {"README.md": "../../outside.md"}}, "outside.md"),
        ({"branch": "-x"}, "branch"),
        ({"branch": ""}, "branch"),
        ({"message": ""}, "message"),
        ({"on_conflict": "merge"}, "on_conflict"),
    ],
)
def test_invalid_configuration_is_refused_clearly(
    ctx: ProjectContext, remote: Path, overrides: dict[str, object], message: str
) -> None:
    cfg = _cfg(remote)
    for key, value in overrides.items():
        if value is None:
            cfg.pop(key, None)
        else:
            cfg[key] = value

    with pytest.raises(GitRepoConfigError, match=message.replace("\\", "\\\\")):
        GitRepoPublisher().plan(ctx, cfg)


def test_a_source_symlinked_out_of_the_project_is_refused(
    ctx: ProjectContext, remote: Path, tmp_path: Path
) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("not for publishing\n", encoding="utf-8")
    (ctx.output_dir / "link.md").symlink_to(secret)

    with pytest.raises(GitRepoConfigError, match="link.md"):
        GitRepoPublisher().plan(ctx, _cfg(remote, files={"README.md": "link.md"}))


# ---------------------------------------------------------------------------
# G2: publish
# ---------------------------------------------------------------------------


def _changed_paths(bare: Path, old: str, new: str) -> list[str]:
    out = _git("--git-dir", str(bare), "diff", "--name-only", old, new)
    return sorted(out.splitlines())


def test_publish_pushes_one_commit_with_only_the_changed_files(
    ctx: ProjectContext, remote: Path
) -> None:
    before = remote_head(remote)
    publisher = GitRepoPublisher()
    plan = publisher.plan(ctx, _cfg(remote, message="chore: refresh profile"))

    result = publisher.publish(ctx, plan)

    assert result.status == "published", result.detail
    after = remote_head(remote)
    assert _git("--git-dir", str(remote), "rev-parse", f"{after}^") == before
    assert _changed_paths(remote, before, after) == ["README.md", "docs/cv.md"]
    assert remote_file(remote, "README.md") == b"# generated\n"
    assert remote_file(remote, "docs/cv.md") == b"# cv\n"
    assert "README.md" in result.detail
    assert "docs/cv.md" in result.detail
    log = _git("--git-dir", str(remote), "log", "-1", "--format=%s|%an|%ae", after)
    assert log == "chore: refresh profile|Test Author|author@example.com"


def test_a_second_run_is_unchanged_and_pushes_nothing(ctx: ProjectContext, remote: Path) -> None:
    publisher = GitRepoPublisher()
    publisher.publish(ctx, publisher.plan(ctx, _cfg(remote)))
    head = remote_head(remote)

    plan = publisher.plan(ctx, _cfg(remote))
    result = publisher.publish(ctx, plan)

    assert list(plan.changes) == []
    assert result.status == "unchanged"
    assert remote_head(remote) == head


def test_publish_carries_binary_files_byte_for_byte(ctx: ProjectContext, remote: Path) -> None:
    publisher = GitRepoPublisher()
    cfg = _cfg(remote, files={"assets/pic.gif": "assets/pic.gif"})
    result = publisher.publish(ctx, publisher.plan(ctx, cfg))

    assert result.status == "published", result.detail
    assert remote_file(remote, "assets/pic.gif") == GIF_BYTES


def test_a_rejected_push_is_failed_not_published(ctx: ProjectContext, remote: Path) -> None:
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'denied by the test remote' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    head = remote_head(remote)
    publisher = GitRepoPublisher()

    result = publisher.publish(ctx, publisher.plan(ctx, _cfg(remote)))

    assert result.status == "failed"
    assert "denied by the test remote" in result.detail
    assert remote_head(remote) == head


def test_a_branch_that_moved_since_the_plan_is_not_overwritten(
    ctx: ProjectContext, remote: Path, tmp_path: Path
) -> None:
    publisher = GitRepoPublisher()
    plan = publisher.plan(ctx, _cfg(remote))

    other = tmp_path / "other"
    _git("clone", str(remote), str(other))
    (other / "README.md").write_text("# edited meanwhile\n", encoding="utf-8")
    _git("commit", "--all", "--message", "meanwhile", cwd=other)
    _git("push", "origin", "HEAD:refs/heads/main", cwd=other)
    moved = remote_head(remote)

    result = publisher.publish(ctx, plan)

    assert result.status == "failed"
    assert "moved" in result.detail
    assert remote_head(remote) == moved


def test_an_unreachable_remote_at_publish_time_is_failed(ctx: ProjectContext, remote: Path) -> None:
    import shutil

    publisher = GitRepoPublisher()
    plan = publisher.plan(ctx, _cfg(remote))
    shutil.rmtree(remote)

    result = publisher.publish(ctx, plan)

    assert result.status == "failed"
    assert "clone" in result.detail


def test_nothing_to_change_publishes_nothing(ctx: ProjectContext, remote: Path) -> None:
    publisher = GitRepoPublisher()
    plan = publisher.plan(ctx, _cfg(remote, files={"same.txt": "same.txt"}))
    head = remote_head(remote)

    assert publisher.publish(ctx, plan).status == "unchanged"
    assert remote_head(remote) == head


def test_without_a_configured_identity_a_fallback_commits(
    ctx: ProjectContext, remote: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.delenv(f"GIT_{role}_NAME")
        monkeypatch.delenv(f"GIT_{role}_EMAIL")
    # Make sure git cannot guess one from the account either.
    monkeypatch.setenv("EMAIL", "")
    publisher = GitRepoPublisher()

    result = publisher.publish(ctx, publisher.plan(ctx, _cfg(remote)))

    assert result.status == "published", result.detail
    author = _git("--git-dir", str(remote), "log", "-1", "--format=%an", "main")
    assert author == "profilekit"


def test_publish_refuses_a_plan_it_did_not_make(ctx: ProjectContext) -> None:
    from profilekit.publishers import PublishPlan

    plan = PublishPlan(destination="x", capability="push", resolved_path=ctx.root, changes=("a",))
    result = GitRepoPublisher().publish(ctx, plan)
    assert result.status == "failed"


def _remote_with_symlink(tmp_path: Path, link: str, target: str) -> Path:
    bare = make_remote(tmp_path, {"README.md": b"# hand-written\n"})
    work = tmp_path / "linker"
    _git("clone", str(bare), str(work))
    (work / link).symlink_to(target)
    _git("add", "--all", cwd=work)
    _git("commit", "--message", "add a link", cwd=work)
    _git("push", "origin", "HEAD:refs/heads/main", cwd=work)
    return bare


def test_a_destination_file_that_is_a_symlink_is_refused(
    ctx: ProjectContext, tmp_path: Path
) -> None:
    bare = _remote_with_symlink(tmp_path, "cv.md", "README.md")
    with pytest.raises(GitRepoConfigError, match="symlink"):
        GitRepoPublisher().plan(ctx, _cfg(bare, files={"cv.md": "cv.md"}))


def test_a_destination_under_a_symlinked_directory_is_not_written(
    ctx: ProjectContext, tmp_path: Path
) -> None:
    bare = _remote_with_symlink(tmp_path, "docs", "..")
    head = remote_head(bare)
    publisher = GitRepoPublisher()

    result = publisher.publish(ctx, publisher.plan(ctx, _cfg(bare, files={"docs/cv.md": "cv.md"})))

    assert result.status == "failed"
    assert "symlink" in result.detail
    assert remote_head(bare) == head


# ---------------------------------------------------------------------------
# G3: wiring into `profile publish`
# ---------------------------------------------------------------------------


def _cli_project(ctx: ProjectContext, remote: Path, extra: str = "", settings: str = "") -> Path:
    (ctx.root / "profile.toml").write_text(
        f"""\
[project]
config_version = 1

[publishers.profile]
kind = "git-repo"
repo = "{remote.as_uri()}"
{settings}
[publishers.profile.files]
"README.md" = "README.md"
"same.txt" = "same.txt"
"docs/cv.md" = "cv.md"
{extra}""",
        encoding="utf-8",
    )
    return ctx.root


def _run(root: Path, *argv: str) -> int:
    from profilekit import cli

    return cli.main(["--project", str(root), "publish", *argv])


def test_git_repo_is_a_registered_publisher_kind() -> None:
    from profilekit import publish, registry

    assert "git-repo" in registry.names(registry.PUBLISHER_GROUP)
    loaded = publish._load_publisher(publish.Destination("x", "git-repo", {}))
    assert isinstance(loaded, GitRepoPublisher)
    assert loaded.capability == "push"
    assert loaded.reads_destination is True


def test_the_entry_point_plans_and_publishes(ctx: ProjectContext, remote: Path) -> None:
    from profilekit.publishers.git_repo import publish_entry_point

    result = publish_entry_point(ctx, _cfg(remote))
    assert result.status == "published", result.detail


def test_dry_run_lists_the_changed_files_and_writes_nothing(
    ctx: ProjectContext, remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')
    head = remote_head(remote)

    assert _run(root) == 0

    row = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("profile"))
    assert "would-publish" in row
    assert "README.md, docs/cv.md" in row
    assert "same.txt" not in row
    assert remote_head(remote) == head
    assert not (root / ".profilekit").exists()


def test_execute_publishes_once_then_reports_unchanged(
    ctx: ProjectContext, remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The seeded README.md was never published by profilekit: replacing it
    # is an explicit choice (see the manual-edit guard below).
    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')
    head = remote_head(remote)

    assert _run(root, "--execute") == 0
    first = remote_head(remote)
    assert _git("--git-dir", str(remote), "rev-list", "--count", f"{head}..{first}") == "1"

    assert _run(root, "--execute") == 0
    assert remote_head(remote) == first
    out = capsys.readouterr().out
    assert "published" in out
    assert "unchanged" in out


def test_a_misconfigured_git_repo_fails_alone(
    ctx: ProjectContext, remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _cli_project(
        ctx,
        remote,
        settings='on_conflict = "overwrite"',
        extra='\n[publishers.broken]\nkind = "git-repo"\nrepo = "owner/name"\n',
    )

    assert _run(root) == 1

    out = capsys.readouterr().out
    broken = next(line for line in out.splitlines() if line.startswith("broken"))
    assert "failed" in broken
    assert "files" in broken
    assert "would-publish" in next(line for line in out.splitlines() if line.startswith("profile"))


# ---------------------------------------------------------------------------
# G4: manual-edit guard
# ---------------------------------------------------------------------------


def _row_of(out: str, name: str) -> str:
    return next(line for line in out.splitlines() if line.startswith(name + " "))


def _hand_edit(remote: Path, tmp_path: Path, path: str, content: str) -> None:
    work = tmp_path / "hand-edit"
    _git("clone", str(remote), str(work))
    (work / path).write_text(content, encoding="utf-8")
    _git("commit", "--all", "--message", "edit by hand", cwd=work)
    _git("push", "origin", "HEAD:refs/heads/main", cwd=work)


def test_a_file_never_published_by_profilekit_is_not_overwritten(
    ctx: ProjectContext, remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _cli_project(ctx, remote)
    head = remote_head(remote)

    assert _run(root) == 1
    dry = _row_of(capsys.readouterr().out, "profile")
    assert "failed" in dry
    assert "README.md" in dry

    assert _run(root, "--execute") == 1
    out = capsys.readouterr().out
    row = _row_of(out, "profile")
    assert "failed" in row
    assert "README.md" in row
    # A file that does not exist yet has nothing to lose.
    assert "docs/cv.md" not in row
    assert 'on_conflict = "overwrite"' in out
    assert remote_head(remote) == head


def test_on_conflict_overwrite_replaces_the_edited_file(
    ctx: ProjectContext, remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')

    assert _run(root, "--execute") == 0

    row = _row_of(capsys.readouterr().out, "profile")
    assert "published" in row
    assert "overwrote" in row
    assert remote_file(remote, "README.md") == b"# generated\n"


def test_a_hand_edit_after_a_publish_blocks_the_next_one(
    ctx: ProjectContext, remote: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')
    assert _run(root, "--execute") == 0
    _cli_project(ctx, remote)  # back to the default: refuse
    _hand_edit(remote, tmp_path, "README.md", "# generated\n\nA hand-written section.\n")
    (ctx.output_dir / "README.md").write_text("# regenerated\n", encoding="utf-8")
    edited = remote_head(remote)
    capsys.readouterr()

    assert _run(root, "--execute") == 1

    row = _row_of(capsys.readouterr().out, "profile")
    assert "failed" in row
    assert "README.md" in row
    assert remote_head(remote) == edited
    assert b"hand-written section" in remote_file(remote, "README.md")


def test_new_content_over_an_untouched_publish_is_not_a_conflict(
    ctx: ProjectContext, remote: Path
) -> None:
    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')
    assert _run(root, "--execute") == 0
    _cli_project(ctx, remote)
    for name in ("README.md", "same.txt", "cv.md"):
        (ctx.output_dir / name).write_text(f"# {name} v2\n", encoding="utf-8")

    assert _run(root, "--execute") == 0

    assert remote_file(remote, "same.txt") == b"# same.txt v2\n"
    assert remote_file(remote, "docs/cv.md") == b"# cv.md v2\n"


def test_a_hand_edit_matching_the_new_content_is_not_a_conflict(
    ctx: ProjectContext, remote: Path, tmp_path: Path
) -> None:
    _hand_edit(remote, tmp_path, "README.md", "# generated\n")
    root = _cli_project(ctx, remote)

    assert _run(root, "--execute") == 0
    assert remote_file(remote, "docs/cv.md") == b"# cv\n"


def test_the_ledger_records_each_file_only_on_execute(ctx: ProjectContext, remote: Path) -> None:
    import hashlib
    import json

    from profilekit import publish

    root = _cli_project(ctx, remote, settings='on_conflict = "overwrite"')
    assert _run(root) == 0
    assert not publish.ledger_path(ctx).exists()

    assert _run(root, "--execute") == 0
    ledger = json.loads(publish.ledger_path(ctx).read_text(encoding="utf-8"))
    for destination, source in (("README.md", "README.md"), ("same.txt", "same.txt")):
        expected = hashlib.sha256((ctx.output_dir / source).read_bytes()).hexdigest()
        assert ledger[publish.ledger_key("profile", destination)] == expected


# ---------------------------------------------------------------------------
# G6: content git normalises on `git add` (line endings, filters)
# ---------------------------------------------------------------------------


@pytest.fixture
def lf_remote(tmp_path: Path) -> Path:
    """A remote that normalises line endings to LF, already holding the LF form."""
    return make_remote(
        tmp_path,
        {".gitattributes": b"* text=auto eol=lf\n", "README.md": b"# generated\n"},
    )


def _crlf_project(ctx: ProjectContext, remote: Path, settings: str = "") -> Path:
    (ctx.output_dir / "README.md").write_bytes(b"# generated\r\n")
    (ctx.root / "profile.toml").write_text(
        f"""\
[project]
config_version = 1

[publishers.profile]
kind = "git-repo"
repo = "{remote.as_uri()}"
{settings}
[publishers.profile.files]
"README.md" = "README.md"
""",
        encoding="utf-8",
    )
    return ctx.root


def test_content_git_normalises_to_what_the_remote_holds_is_unchanged(
    ctx: ProjectContext, lf_remote: Path
) -> None:
    _crlf_project(ctx, lf_remote)
    plan = GitRepoPublisher().plan(ctx, _cfg(lf_remote, files={"README.md": "README.md"}))
    assert list(plan.changes) == []


def test_a_normalised_publish_does_not_conflict_on_the_next_run(
    ctx: ProjectContext, lf_remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _crlf_project(ctx, lf_remote, settings='on_conflict = "overwrite"')
    (ctx.output_dir / "README.md").write_bytes(b"# v2\r\n")
    assert _run(root, "--execute") == 0
    assert remote_file(lf_remote, "README.md") == b"# v2\n"

    _crlf_project(ctx, lf_remote)  # default: refuse
    (ctx.output_dir / "README.md").write_bytes(b"# v3\r\n")
    capsys.readouterr()

    assert _run(root, "--execute") == 0, capsys.readouterr().out
    assert remote_file(lf_remote, "README.md") == b"# v3\n"


def test_overwrite_does_not_promise_a_change_git_normalises_away(
    ctx: ProjectContext, lf_remote: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _crlf_project(ctx, lf_remote, settings='on_conflict = "overwrite"')

    assert _run(root) == 0

    row = _row_of(capsys.readouterr().out, "profile")
    assert "unchanged" in row
    assert "would" not in row


# ---------------------------------------------------------------------------
# G7: credentials never travel in `repo`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "repo",
    [
        "https://user:hunter2@example.com/a/b.git",
        "https://ghp_faketoken@example.com/a/b.git",
        "http://user@example.com/a/b.git",
    ],
)
def test_a_repo_url_with_credentials_is_refused(ctx: ProjectContext, repo: str) -> None:
    with pytest.raises(GitRepoConfigError, match="credential helper") as caught:
        GitRepoPublisher().plan(ctx, {"repo": repo, "files": {"README.md": "README.md"}})
    assert "hunter2" not in str(caught.value)
    assert "ghp_faketoken" not in str(caught.value)


@pytest.mark.parametrize(
    "repo",
    [
        "git@github.com:owner/name.git",
        "ssh://git@example.com/owner/name.git",
        "https://example.com/owner/name.git",
    ],
)
def test_ssh_and_plain_https_urls_are_accepted(repo: str) -> None:
    from profilekit.publishers.git_repo import check_repo

    assert check_repo(repo) == repo


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        ("fatal: unable to access 'https://user:hunter2@example.com/a.git/'", "hunter2"),
        ("cannot clone https://ghp_faketoken@example.com/a.git", "ghp_faketoken"),
        ("ssh://git:hunter2@example.com/a.git", "hunter2"),
    ],
)
def test_redact_removes_userinfo_from_details(text: str, secret: str) -> None:
    from profilekit.publishers.git_repo import redact

    redacted = redact(text)
    assert secret not in redacted
    assert "example.com" in redacted


def test_git_errors_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whatever git prints on failure is redacted before it reaches a detail."""
    from profilekit.publishers import git_repo

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        stderr = b"fatal: unable to access 'https://user:hunter2@example.com/a.git/'"
        return subprocess.CompletedProcess(command, 128, b"", stderr)

    monkeypatch.setattr(git_repo.subprocess, "run", fake_run)
    with pytest.raises(GitCommandError) as caught:
        git_repo.run_git("ls-remote", "origin")
    assert "hunter2" not in str(caught.value)
    assert "example.com" in str(caught.value)
