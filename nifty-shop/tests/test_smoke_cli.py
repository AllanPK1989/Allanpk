from __future__ import annotations

import pytest

from nifty_shop.smoke import MissingCredentialsError, build_client, credentials_from_env


def full_env() -> dict[str, str]:
    return {
        "FIRSTOCK_USER_ID": "AB1234",
        "FIRSTOCK_PASSWORD": "pw",
        "FIRSTOCK_TOTP_SECRET": "JBSWY3DPEHPK3PXP",
        "FIRSTOCK_API_KEY": "key",
        "FIRSTOCK_VENDOR_CODE": "AB1234_U",
        "EXPECTED_EGRESS_IP": "203.0.113.7",
    }


def test_reads_every_credential_from_the_environment() -> None:
    creds = credentials_from_env(full_env())
    assert creds.user_id == "AB1234"
    assert creds.vendor_code == "AB1234_U"
    assert creds.expected_egress_ip == "203.0.113.7"


@pytest.mark.parametrize(
    "missing",
    [
        "FIRSTOCK_USER_ID",
        "FIRSTOCK_PASSWORD",
        "FIRSTOCK_TOTP_SECRET",
        "FIRSTOCK_API_KEY",
        "FIRSTOCK_VENDOR_CODE",
        "EXPECTED_EGRESS_IP",
    ],
)
def test_any_missing_credential_refuses_and_names_it(missing: str) -> None:
    env = full_env()
    del env[missing]
    with pytest.raises(MissingCredentialsError, match=missing):
        credentials_from_env(env)


def test_a_blank_value_counts_as_missing() -> None:
    env = full_env()
    env["FIRSTOCK_API_KEY"] = "   "
    with pytest.raises(MissingCredentialsError, match="FIRSTOCK_API_KEY"):
        credentials_from_env(env)


def test_credentials_repr_never_leaks_the_password_or_totp_secret() -> None:
    creds = credentials_from_env(full_env())
    rendered = repr(creds)
    assert "pw" not in rendered
    assert "JBSWY3DPEHPK3PXP" not in rendered


def test_build_client_wires_the_identifiers_through() -> None:
    client = build_client(credentials_from_env(full_env()))
    assert client.user_id == "AB1234"
    assert client.is_logged_in is False


def test_totp_provider_generates_a_six_digit_code() -> None:
    creds = credentials_from_env(full_env())
    code = creds.totp_provider()
    assert len(code) == 6
    assert code.isdigit()
