"""Git repository publisher — generated artifacts into another repository.

The artifacts this project generates are served from other repositories: a
GitHub profile README, a CV repository, a portfolio site. Refreshing them by
hand means cloning each one, copying files in, committing and pushing. This
publisher does exactly that, and nothing more, for every repository declared
as a ``git-repo`` destination::

    [publishers.profile-readme]
    kind = "git-repo"
    repo = "owner/owner"            # or any git URL or path
    branch = "main"                 # default
    message = "chore: refresh"      # default: DEFAULT_MESSAGE
    on_conflict = "refuse"          # default; or "overwrite"

    [publishers.profile-readme.files]
    "README.md" = "README.md"       # destination path = source path
    "assets/hero.gif" = "assets/hero.gif"

A source resolves against the generated output directory first, then the
project root, and must stay inside the one it resolved against.

``git`` is driven through its CLI with argument lists, never a shell.
Credentials are whatever the user's git already uses — a credential helper,
``gh auth``, an SSH agent. This module never reads, asks for, or stores a
token.

``plan()`` clones the branch shallowly into a temporary directory, compares
each mapped file with what the branch holds, and removes the clone. It writes
nothing to the project or the remote.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from profilekit.publishers import (
    Artifact,
    Capability,
    ProjectContext,
    PublishPlan,
    PublishResult,
)
from profilekit.safe_io import write_file

DEFAULT_BRANCH = "main"
DEFAULT_MESSAGE = "chore: update generated profile artifacts"

# Used only when git cannot determine the user's own identity: the user's
# configured name and email always win.
FALLBACK_NAME = "profilekit"
FALLBACK_EMAIL = "profilekit@localhost"
ON_CONFLICT_CHOICES = ("refuse", "overwrite")

# `owner/name` is GitHub shorthand. Anything else — a URL, an scp-style
# address, a path — is handed to git as written.
_GITHUB_SHORTHAND = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")


class GitRepoConfigError(ValueError):
    """Raised when a ``git-repo`` destination's configuration cannot be honored."""


class GitCommandError(RuntimeError):
    """Raised when ``git`` fails or is not installed; carries git's own message."""


@dataclass(frozen=True)
class GitRepoPlan(PublishPlan):
    """A plan that also carries where and how to commit.

    ``remote_digest`` is the commit the branch pointed at when the plan was
    made, so ``publish()`` can tell when the branch moved in between.
    """

    repo: str = ""
    branch: str = DEFAULT_BRANCH
    message: str = DEFAULT_MESSAGE
    on_conflict: str = "refuse"


@dataclass(frozen=True)
class _Config:
    repo: str
    branch: str
    message: str
    on_conflict: str
    files: tuple[tuple[str, str], ...]


def resolve_repo(repo: str) -> str:
    """Expand GitHub ``owner/name`` shorthand; return anything else unchanged."""
    if _GITHUB_SHORTHAND.match(repo):
        return f"https://github.com/{repo}.git"
    return repo


def _text(cfg: Mapping[str, object], key: str, default: str | None) -> str:
    value = cfg.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise GitRepoConfigError(f"{key!r} must be a non-empty string, got {value!r}")
    if value.startswith("-"):
        # Would be parsed as an option by git.
        raise GitRepoConfigError(f"{key!r} must not start with '-': {value!r}")
    return value


def _parse_config(cfg: Mapping[str, object]) -> _Config:
    repo = resolve_repo(_text(cfg, "repo", None))
    branch = _text(cfg, "branch", DEFAULT_BRANCH)
    message = cfg.get("message", DEFAULT_MESSAGE)
    if not isinstance(message, str) or not message.strip():
        raise GitRepoConfigError(f"'message' must be a non-empty string, got {message!r}")
    on_conflict = cfg.get("on_conflict", "refuse")
    if on_conflict not in ON_CONFLICT_CHOICES:
        raise GitRepoConfigError(
            f"'on_conflict' must be one of {', '.join(ON_CONFLICT_CHOICES)}, got {on_conflict!r}"
        )

    files = cfg.get("files")
    if not isinstance(files, Mapping) or not files:
        raise GitRepoConfigError(
            "'files' must be a non-empty table of destination path = source path"
        )
    pairs: list[tuple[str, str]] = []
    for destination, source in files.items():
        if not isinstance(source, str) or not source:
            raise GitRepoConfigError(
                f"files.{destination!r} must name a source path, got {source!r}"
            )
        pairs.append((_destination_path(str(destination)), source))

    return _Config(
        repo=repo,
        branch=branch,
        message=message,
        on_conflict=str(on_conflict),
        files=tuple(pairs),
    )


def _destination_path(path: str) -> str:
    """Validate a path inside the destination repository; return it normalized."""
    if "\\" in path:
        raise GitRepoConfigError(f"destination path must use '/', not a backslash: {path!r}")
    pure = PurePosixPath(path)
    if not path or pure.is_absolute():
        raise GitRepoConfigError(f"destination path must be relative to the repository: {path!r}")
    if any(part in ("..", ".") for part in pure.parts) or not pure.parts:
        raise GitRepoConfigError(f"destination path must stay inside the repository: {path!r}")
    if any(part.lower() == ".git" for part in pure.parts):
        raise GitRepoConfigError(f"destination path must not touch .git: {path!r}")
    return pure.as_posix()


def resolve_source(ctx: ProjectContext, source: str) -> Path:
    """Find *source* in the output directory, then the project root.

    A source must stay inside the directory it resolved against, after
    following symlinks: whatever it names is pushed to a remote, so a link
    pointing out of the project would publish a file nobody chose to publish.
    """
    if Path(source).is_absolute():
        raise GitRepoConfigError(
            f"source path must be relative to the output directory or project root: {source!r}"
        )
    for base in (ctx.output_dir, ctx.root):
        resolved_base = base.resolve()
        candidate = (resolved_base / source).resolve()
        if candidate != resolved_base and resolved_base not in candidate.parents:
            if (base / source).exists():
                raise GitRepoConfigError(
                    f"source {source!r} resolves outside {resolved_base}: {candidate}"
                )
            continue
        if candidate.is_file():
            return candidate
    raise GitRepoConfigError(
        f"source {source!r} not found in {ctx.output_dir} or {ctx.root} "
        "(generate it first, or fix the path)"
    )


def _artifact(name: str, data: bytes) -> Artifact:
    try:
        return Artifact(name, data.decode("utf-8"))
    except UnicodeDecodeError:
        return Artifact(name, "", data=data)


def _git_executable() -> str:
    found = shutil.which("git")
    if found is None:
        raise GitCommandError("git is not installed or not on PATH")
    return found


def run_git(*args: str, cwd: Path | None = None) -> bytes:
    """Run ``git`` with *args* and return its stdout; raise on failure.

    The argument list goes straight to the executable: no shell, so nothing in
    a configured value is ever interpreted. The ``ext::`` transport, which runs
    an arbitrary command, is refused whatever the user's configuration says.

    The environment is inherited untouched — that is how the user's own
    credential helpers, SSH agent and identity reach git. Reading it here
    would also break the rule that a publisher never inspects the environment
    (``tests/test_secrets.py``).
    """
    command = [_git_executable(), "-c", "protocol.ext.allow=never", *args]
    # S603: an argument list, no shell; the values come from profile.toml and
    # are validated above, and git itself is resolved through PATH explicitly.
    result = subprocess.run(  # noqa: S603
        command, cwd=cwd, capture_output=True, check=False
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitCommandError(f"git {args[0]} failed: {detail or f'exit {result.returncode}'}")
    return result.stdout


def clone(repo: str, branch: str, directory: Path) -> str:
    """Shallow-clone *branch* of *repo* into *directory*; return its commit."""
    try:
        run_git(
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            branch,
            "--",
            repo,
            str(directory),
        )
    except GitCommandError as exc:
        raise GitCommandError(f"cannot clone branch {branch!r} of {repo}: {exc}") from exc
    return run_git("rev-parse", "HEAD", cwd=directory).decode().strip()


def read_tracked(clone_dir: Path, path: str) -> bytes | None:
    """Return the committed content of *path*, or ``None`` when it is absent.

    Read from git's object store rather than the checkout, so a symlink in
    the destination repository is compared as the link it is, never followed.
    """
    listing = run_git("--literal-pathspecs", "ls-tree", "-z", "HEAD", "--", path, cwd=clone_dir)
    entry = listing.split(b"\0", 1)[0]
    if not entry:
        return None
    meta, _, _name = entry.partition(b"\t")
    mode, kind, object_id = meta.decode().split()
    if kind != "blob" or mode == "120000":
        raise GitRepoConfigError(
            f"destination path {path!r} is a {'symlink' if mode == '120000' else kind} "
            "in the repository, not a file"
        )
    return run_git("cat-file", "blob", object_id, cwd=clone_dir)


def commit_identity(clone_dir: Path) -> list[str]:
    """Return ``-c`` options for a fallback identity, or none when git has one.

    The user's own identity — from their git config or ``GIT_*`` variables —
    is what a commit in their repository should carry. Only when git cannot
    determine one does the commit fall back to a neutral profilekit identity
    rather than failing the publish.
    """
    try:
        run_git("var", "GIT_AUTHOR_IDENT", cwd=clone_dir)
        run_git("var", "GIT_COMMITTER_IDENT", cwd=clone_dir)
    except GitCommandError:
        return ["-c", f"user.name={FALLBACK_NAME}", "-c", f"user.email={FALLBACK_EMAIL}"]
    return []


def _checked_target(clone_dir: Path, name: str) -> Path:
    """Return where *name* goes in the clone, refusing a symlinked directory on the way."""
    target = clone_dir / name
    for ancestor in reversed(target.relative_to(clone_dir).parents):
        if (clone_dir / ancestor).is_symlink():
            raise GitRepoConfigError(
                f"destination path {name!r} goes through a symlink in the repository: {ancestor}"
            )
    return target


class GitRepoPublisher:
    """Commits generated artifacts into a git repository and pushes them."""

    kind: str = "git-repo"
    capability: Capability = "push"
    reads_destination: bool = True

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> GitRepoPlan:
        """Compute which mapped files differ from the remote branch.

        Configuration is validated and every source read before the network is
        touched, so a typo fails fast and never waits on a clone.
        """
        config = _parse_config(cfg)
        artifacts = [
            _artifact(destination, resolve_source(ctx, source).read_bytes())
            for destination, source in config.files
        ]

        with tempfile.TemporaryDirectory(prefix="profilekit-git-") as scratch:
            clone_dir = Path(scratch) / "repo"
            head = clone(config.repo, config.branch, clone_dir)
            current = {a.name: read_tracked(clone_dir, a.name) for a in artifacts}

        changes = [a.name for a in artifacts if current[a.name] != a.encoded()]
        return GitRepoPlan(
            destination=config.repo,
            capability=self.capability,
            resolved_path=ctx.root,
            artifacts=tuple(artifacts),
            changes=tuple(changes),
            remote_digest=head,
            repo=config.repo,
            branch=config.branch,
            message=config.message,
            on_conflict=config.on_conflict,
        )

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Commit the planned changes in a fresh clone and push them.

        The clone is made again rather than kept from ``plan()``: a dry run
        never reaches here, and a clone held open between the two would leak
        a temporary directory on every dry run. If the branch moved since the
        plan, nothing is written: the plan no longer describes the remote.

        Every failure — clone, commit, push, a refused path — comes back as
        this destination's ``failed`` with git's own message. A push that did
        not happen is never reported as ``published``.
        """
        if not isinstance(plan, GitRepoPlan):
            return PublishResult(
                destination=plan.destination,
                status="failed",
                detail="not a git-repo plan; plan() must come from GitRepoPublisher",
            )
        if not plan.changes:
            return PublishResult(
                destination=plan.destination,
                status="unchanged",
                detail=f"{plan.repo} ({plan.branch}) already matches the artifacts",
            )

        try:
            commit = self._commit_and_push(plan)
        except (GitCommandError, GitRepoConfigError, OSError) as exc:
            return PublishResult(destination=plan.destination, status="failed", detail=str(exc))

        if commit is None:
            return PublishResult(
                destination=plan.destination,
                status="unchanged",
                detail=f"{plan.repo} ({plan.branch}) already matches the artifacts",
            )
        written = ", ".join(plan.changes)
        return PublishResult(
            destination=plan.destination,
            status="published",
            detail=(
                f"pushed {commit[:12]} to {plan.repo} ({plan.branch}) with "
                f"{len(plan.changes)} file(s): {written}"
            ),
        )

    @staticmethod
    def _commit_and_push(plan: GitRepoPlan) -> str | None:
        """Write, commit and push; return the new commit, or ``None`` if nothing differed."""
        with tempfile.TemporaryDirectory(prefix="profilekit-git-") as scratch:
            clone_dir = Path(scratch) / "repo"
            head = clone(plan.repo, plan.branch, clone_dir)
            if plan.remote_digest is not None and head != plan.remote_digest:
                raise GitCommandError(
                    f"{plan.repo} ({plan.branch}) moved since the plan "
                    f"({plan.remote_digest[:12]} -> {head[:12]}); re-run to plan again"
                )

            changed = [a for a in plan.artifacts if a.name in plan.changes]
            # Every target is checked before the first write, so a refused
            # path cannot leave a half-written clone behind to commit.
            targets = [(_checked_target(clone_dir, a.name), a) for a in changed]
            for target, artifact in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                write_file(target, artifact.encoded(), root=clone_dir, overwrite=True)

            names = [a.name for a in changed]
            run_git("--literal-pathspecs", "add", "--", *names, cwd=clone_dir)
            staged = run_git("diff", "--cached", "--name-only", cwd=clone_dir)
            if not staged.strip():
                # No empty commits: the content already matched.
                return None
            run_git(
                *commit_identity(clone_dir),
                "commit",
                "--quiet",
                "--message",
                plan.message,
                cwd=clone_dir,
            )
            run_git("push", "--quiet", "origin", f"HEAD:refs/heads/{plan.branch}", cwd=clone_dir)
            return run_git("rev-parse", "HEAD", cwd=clone_dir).decode().strip()


def publish_entry_point(
    ctx: ProjectContext,
    cfg: Mapping[str, object] | None = None,
    credentials: Mapping[str, object] | None = None,
) -> PublishResult:
    """Registry entry point: plan and publish in one call.

    Registered as the ``git-repo`` publisher. profilekit itself never calls
    it: ``publish._load_publisher`` maps this entry point to
    :class:`GitRepoPublisher`, so a destination keeps its two phases — a dry
    run plans and never pushes — and reads its own destination for staleness.
    It stays callable for code outside the package that loads the entry point
    directly. *credentials* is accepted for the uniform signature and unused:
    git authenticates with the user's own helpers.
    """
    publisher = GitRepoPublisher()
    return publisher.publish(ctx, publisher.plan(ctx, cfg or {}))


__all__ = [
    "DEFAULT_BRANCH",
    "DEFAULT_MESSAGE",
    "FALLBACK_EMAIL",
    "FALLBACK_NAME",
    "GitCommandError",
    "GitRepoConfigError",
    "GitRepoPlan",
    "GitRepoPublisher",
    "publish_entry_point",
    "resolve_repo",
    "resolve_source",
]
