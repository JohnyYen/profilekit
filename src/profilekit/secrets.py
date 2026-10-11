"""Credential handling for the publication layer.

A token printed once in a traceback ends up in CI logs, which are often
world-readable and retained far longer than the token's lifetime. The paths
that leak are not the obvious ones — nobody writes ``print(token)`` on
purpose. They are ``repr()`` inside a container, f-string interpolation in a
log line, and the automatic ``repr`` of local variables that Python includes
in an exception.

So a credential is wrapped in :class:`Secret`, whose every string conversion
is redacted, and reading the value requires an explicit ``.reveal()`` — a
greppable call that shows up in review rather than hiding inside an
interpolation.

Publishers never read the environment. The core resolves credentials from
``[publishers.X.credential]`` and injects them, which keeps the set of secrets
a publisher can see declared in ``profile.toml`` and auditable there. A
publisher reading ``os.environ`` directly would quietly widen its own access,
and a test asserts none does.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

REDACTED = "<redacted>"


class MissingCredentialError(Exception):
    """Raised when a declared credential is not available in the environment.

    Distinct from "no credential declared" on purpose. An unset variable that
    resolved to an empty string would let a publisher authenticate with
    nothing and surface a confusing upstream error instead of a configuration
    one.
    """

    exit_code = 1


class Secret:
    """A credential value that does not appear in any string conversion.

    ``__slots__`` keeps the value out of an instance ``__dict__``, which some
    debuggers and serializers walk indiscriminately. Serialisation is refused
    outright — see ``__reduce__``.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        """Return the underlying value.

        Deliberately a named method rather than a property or ``__str__``: the
        call site is then greppable, and no accidental interpolation can read
        it.
        """
        return self._value

    def __repr__(self) -> str:
        return f"Secret({REDACTED})"

    def __str__(self) -> str:
        return REDACTED

    def __format__(self, _spec: str) -> str:
        # Covers f-strings, which call __format__ rather than __str__.
        return REDACTED

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Secret):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __reduce__(self) -> tuple:  # type: ignore[type-arg]
        """Refuse to serialise.

        Pickle reads `__slots__` directly, so the default behaviour writes the
        raw value into the blob — and pickling happens implicitly in
        `multiprocessing`, in some caching layers, and in crash dumps. A
        credential that silently lands on disk that way is exactly the leak
        this class exists to prevent.

        Nothing has a legitimate reason to pickle a credential: a process that
        needs one resolves it from the environment itself. So this fails loudly
        rather than succeeding quietly.
        """
        raise TypeError(
            "Secret cannot be serialised: pickling would write the credential "
            "in clear text. Resolve it from the environment where it is needed."
        )


class CredentialSet(dict[str, Secret]):
    """The credentials injected into one destination.

    A plain mapping of name to :class:`Secret`. Subclassed so a credential set
    is recognisable in a signature, and so its ``repr`` inherits the redaction
    of its values.
    """


def resolve(cfg: Mapping[str, Any], *, destination: str) -> CredentialSet:
    """Resolve the credentials declared by one destination's configuration.

    Reads ``[publishers.X.credential]`` entries of the form ``env = "NAME"``.
    A destination that needs no credential — the ``filesystem`` and ``manual``
    kinds — declares none and gets an empty set rather than being forced to
    invent one.
    """
    declaration = cfg.get("credential")
    if not isinstance(declaration, dict):
        return CredentialSet({})

    resolved = CredentialSet({})
    for key, variable in declaration.items():
        if not isinstance(variable, str):
            raise MissingCredentialError(
                f"destination {destination!r}: credential {key!r} must name an environment variable"
            )

        value = os.environ.get(variable)
        if not value:
            raise MissingCredentialError(
                f"destination {destination!r}: environment variable {variable!r} "
                "is not set or is empty"
            )
        resolved[key] = Secret(value)

    return resolved


__all__ = [
    "REDACTED",
    "CredentialSet",
    "MissingCredentialError",
    "Secret",
    "resolve",
]
