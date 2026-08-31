from __future__ import annotations

from nifty_shop.redaction import REDACTED, redact


def test_redacts_the_session_token() -> None:
    assert redact({"jKey": "abc123", "userId": "AB1234"}) == {
        "jKey": REDACTED,
        "userId": "AB1234",
    }


def test_key_matching_is_case_insensitive() -> None:
    """The API uses jKey, TOTP and apiKey; casing must not create a leak."""
    out = redact({"TOTP": "123456", "apiKey": "k", "Password": "p"})
    assert out == {"TOTP": REDACTED, "apiKey": REDACTED, "Password": REDACTED}


def test_redacts_nested_structures() -> None:
    payload = {"data": {"susertoken": "tok"}, "orders": [{"jKey": "tok"}]}
    assert redact(payload) == {
        "data": {"susertoken": REDACTED},
        "orders": [{"jKey": REDACTED}],
    }


def test_non_secret_values_survive_untouched() -> None:
    payload = {"status": "success", "quantity": 7, "price": None, "tags": ["a", "b"]}
    assert redact(payload) == payload


def test_secret_value_never_appears_in_the_output() -> None:
    secret = "super-secret-token-value"
    rendered = repr(redact({"outer": {"susertoken": secret}}))
    assert secret not in rendered
