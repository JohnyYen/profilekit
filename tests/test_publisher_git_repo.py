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
