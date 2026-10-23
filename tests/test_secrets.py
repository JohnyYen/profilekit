"""Credentials must not leak through the channels that leak by accident.

A token that is printed once in a traceback ends up in CI logs, which are
often world-readable and retained far longer than the token's lifetime. The
dangerous paths are not the obvious ones — nobody writes `print(token)` on
purpose. They are `repr()` inside a container, f-string interpolation in a log
line, and the automatic `repr` of local variables in an exception.

So the value is wrapped in a type whose every string conversion is redacted,
and reading it requires an explicit, greppable call.

Publishers never touch `os.environ`. The core resolves credentials from
configuration and injects them, which means the set of secrets a publisher can
see is declared in `profile.toml` and auditable there.
"""

from __future__ import annotations

import pytest

from profilekit.config import ConfigError
from profilekit.secrets import (
    CredentialDeclarationError,
    CredentialSet,
    MissingCredentialError,
    Secret,
    resolve,
    validate_declaration,
)

TOKEN = "ghp_verySecretValue123"


# ---------------------------------------------------------------------------
# Every string conversion is redacted
# ---------------------------------------------------------------------------


def test_repr_does_not_contain_the_value() -> None:
    assert TOKEN not in repr(Secret(TOKEN))


def test_str_does_not_contain_the_value() -> None:
    assert TOKEN not in str(Secret(TOKEN))


def test_f_string_does_not_contain_the_value() -> None:
    """The most likely accident: interpolating a secret into a log line."""
    secret = Secret(TOKEN)
    assert TOKEN not in f"authenticating with {secret}"


def test_repr_inside_a_container_does_not_leak() -> None:
    """A dict of credentials printed for debugging must stay redacted."""
    bundle = {"github": Secret(TOKEN)}
    assert TOKEN not in repr(bundle)


def test_traceback_does_not_leak_the_value() -> None:
    """Local variables appear in tracebacks; a raw string would be captured."""
    import traceback

    secret = Secret(TOKEN)
    try:
        raise RuntimeError(f"failed while using {secret}")
    except RuntimeError:
        rendered = traceback.format_exc()

    assert TOKEN not in rendered


def test_redaction_marker_is_recognisable() -> None:
    """Redacted output must be obviously redacted, not an empty string."""
    assert "redacted" in repr(Secret(TOKEN)).lower()


def test_reading_the_value_is_explicit() -> None:
    """Retrieval must be a greppable call, not an attribute read or a cast."""
    assert Secret(TOKEN).reveal() == TOKEN


def test_secret_is_not_iterable_or_sliceable() -> None:
    """Accidental string-like use must fail loudly rather than half-work."""
    secret = Secret(TOKEN)
    with pytest.raises(TypeError):
        _ = secret[0:3]  # type: ignore[index]


def test_equality_does_not_require_revealing() -> None:
    assert Secret(TOKEN) == Secret(TOKEN)
    assert Secret(TOKEN) != Secret("other")


# ---------------------------------------------------------------------------
# The core resolves; publishers never read the environment
# ---------------------------------------------------------------------------


def test_resolve_reads_the_declared_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MY_TOKEN", TOKEN)
    credentials = resolve({"credential": {"env": "MY_TOKEN"}}, destination="acme")

    assert credentials["env"].reveal() == TOKEN


def test_resolve_returns_an_empty_set_when_none_is_declared() -> None:
    """A destination needing no credential must not be forced to declare one."""
    assert resolve({}, destination="filesystem-dest") == CredentialSet({})


def test_missing_credential_is_reported_not_silently_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset variable must be distinguishable from an absent declaration.

    Returning an empty string would let a publisher authenticate with nothing
    and report a confusing upstream error instead of a configuration one.
    """
    monkeypatch.delenv("MY_TOKEN", raising=False)

    with pytest.raises(MissingCredentialError) as exc_info:
        resolve({"credential": {"env": "MY_TOKEN"}}, destination="acme")

    message = str(exc_info.value)
    assert "MY_TOKEN" in message
    assert "acme" in message


def test_the_error_message_does_not_contain_any_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a wrong value must not be echoed back into the logs."""
    monkeypatch.setenv("MY_TOKEN", "")

    with pytest.raises(MissingCredentialError) as exc_info:
        resolve({"credential": {"env": "MY_TOKEN"}}, destination="acme")

    assert TOKEN not in str(exc_info.value)


@pytest.mark.parametrize(
    ("declaration", "field"),
    [
        ("MY_TOKEN", "credential"),
        ({"token": 42}, "credential.token"),
        ({"token": {"env": "MY_TOKEN"}}, "credential.token"),
        ({"token": ""}, "credential.token"),
    ],
)
def test_a_malformed_declaration_is_a_configuration_error_not_a_missing_credential(
    monkeypatch: pytest.MonkeyPatch, declaration: object, field: str
) -> None:
    """A typo in profile.toml must not masquerade as an unset variable.

    Treated as missing, it was reported `skipped` with exit 0 — the operator
    saw a benign state while the destination could never have published.
    """
    monkeypatch.setenv("MY_TOKEN", TOKEN)

    with pytest.raises(CredentialDeclarationError) as exc_info:
        resolve({"credential": declaration}, destination="acme")

    error = exc_info.value
    assert not isinstance(error, MissingCredentialError)
    assert isinstance(error, ConfigError)
    assert error.exit_code == 2
    assert "'acme'" in str(error)
    assert field in str(error)
    assert TOKEN not in str(error)


def test_validate_declaration_does_not_read_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation is shape-only, so an absent variable is not its concern."""
    monkeypatch.delenv("MY_TOKEN", raising=False)

    validate_declaration({"credential": {"env": "MY_TOKEN"}}, destination="acme")
    validate_declaration({}, destination="acme")
    with pytest.raises(CredentialDeclarationError, match=r"credential\.env"):
        validate_declaration({"credential": {"env": 1}}, destination="acme")


def test_publishers_do_not_read_the_environment() -> None:
    """Structural: no shipped publisher may call os.environ itself.

    If a publisher reads the environment directly, the set of secrets it can
    see stops being declared in configuration and stops being auditable.
    """
    import inspect

    from profilekit.publishers import filesystem

    for module in (filesystem,):
        source = inspect.getsource(module)
        assert "os.environ" not in source, (
            f"{module.__name__} must receive credentials, not read them"
        )
        assert "getenv" not in source, f"{module.__name__} must receive credentials, not read them"


def test_secret_refuses_to_pickle() -> None:
    """Pickle reads __slots__ directly, so the default behaviour leaks the value.

    This matters because pickling happens implicitly — `multiprocessing`,
    caching layers, crash dumps. A credential that silently lands on disk that
    way defeats every other redaction in this class.
    """
    import pickle

    with pytest.raises(TypeError) as exc_info:
        pickle.dumps(Secret(TOKEN))

    assert TOKEN not in str(exc_info.value), "even the refusal must not echo the value"


def test_a_credential_set_cannot_be_pickled_either() -> None:
    """The container must not become a way around the refusal."""
    import pickle

    with pytest.raises(TypeError):
        pickle.dumps(CredentialSet({"token": Secret(TOKEN)}))


def test_deepcopy_is_refused_rather_than_leaking() -> None:
    """`copy` falls back to `__reduce__`, so deep-copying a Secret is refused.

    A deliberate trade, and stated narrowly: copying a **Secret itself** is
    refused, shallow or deep. A shallow copy of a *container* holding one
    succeeds, because it copies the container and not its members — the
    Secret is shared, which is the supported way to carry it. Only a deep copy
    of such a container reaches the reduce path and fails.

    Refusing beats the alternative: a copy whose value is exposed through that
    same path. Code needing a second reference shares the Secret; code needing
    the value calls `.reveal()`.
    """
    import copy

    with pytest.raises(TypeError):
        copy.deepcopy(Secret(TOKEN))

    # Shallow copy of the Secret itself goes through the same reduce path.
    with pytest.raises(TypeError):
        copy.copy(Secret(TOKEN))

    # But a shallow copy of a container holding one works, because it does not
    # copy the members. This is the supported way to pass a credential along.
    secret = Secret(TOKEN)
    shallow = copy.copy({"token": secret})
    assert shallow["token"] is secret

    # A deep copy of that container does reach the refusal.
    with pytest.raises(TypeError):
        copy.deepcopy({"token": secret})
