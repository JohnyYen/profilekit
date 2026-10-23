"""Behavior pinned down by mutation testing of ``profilekit.secrets``.

Each test here kills mutants that survived the baseline run (see
``docs/quality/mutation-baseline.md``). The existing suite proved that errors
are *raised*; these assert what the error *says*, because the message is the
only thing an operator reading a CI log gets to act on.
"""

from __future__ import annotations

import pickle

import pytest

from profilekit.secrets import (
    CredentialDeclarationError,
    MissingCredentialError,
    Secret,
    resolve,
    validate_declaration,
)


def test_pickling_a_secret_explains_the_refusal_and_how_to_get_the_value() -> None:
    with pytest.raises(TypeError) as excinfo:
        pickle.dumps(Secret("hunter2"))

    assert str(excinfo.value) == (
        "Secret cannot be serialised: pickling would write the credential "
        "in clear text. Resolve it from the environment where it is needed."
    )
    assert "hunter2" not in str(excinfo.value)


def test_secret_truthiness_follows_its_value() -> None:
    assert bool(Secret("token")) is True
    assert bool(Secret("")) is False


def test_distinct_secrets_hash_differently_and_equal_ones_alike() -> None:
    assert hash(Secret("alpha")) == hash(Secret("alpha"))
    assert hash(Secret("alpha")) != hash(Secret("beta"))
    assert len({Secret("alpha"), Secret("alpha"), Secret("beta")}) == 2


@pytest.mark.parametrize(
    ("declaration", "type_name"),
    [("TOKEN_VAR", "str"), (["TOKEN_VAR"], "list"), (3, "int")],
)
def test_non_table_declaration_names_the_type_it_got(declaration: object, type_name: str) -> None:
    with pytest.raises(CredentialDeclarationError) as excinfo:
        validate_declaration({"credential": declaration}, destination="site")

    assert str(excinfo.value) == (
        "destination 'site': credential must be a table of "
        f'name = "ENV_VAR" entries, got {type_name}'
    )


@pytest.mark.parametrize(
    ("variable", "got"),
    [(42, "int"), (None, "NoneType"), (["A"], "list"), ("", "an empty string")],
)
def test_bad_credential_entry_names_the_key_and_what_was_found(variable: object, got: str) -> None:
    with pytest.raises(CredentialDeclarationError) as excinfo:
        validate_declaration({"credential": {"token": variable}}, destination="site")

    assert str(excinfo.value) == (
        f"destination 'site': credential.token must name an environment variable, got {got}"
    )


def test_unset_variable_message_names_destination_and_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROFILEKIT_TEST_UNSET_TOKEN", raising=False)

    with pytest.raises(MissingCredentialError) as excinfo:
        resolve({"credential": {"token": "PROFILEKIT_TEST_UNSET_TOKEN"}}, destination="site")

    assert str(excinfo.value) == (
        "destination 'site': environment variable 'PROFILEKIT_TEST_UNSET_TOKEN' "
        "is not set or is empty"
    )
