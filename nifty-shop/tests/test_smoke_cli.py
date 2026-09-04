from __future__ import annotations

from pathlib import Path

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


# --- .env loading, so the same commands work on Windows and Linux -----------------

def test_dotenv_values_are_loaded(tmp_path: Path) -> None:
    from nifty_shop.smoke import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("FIRSTOCK_USER_ID=AB1234\nEXPECTED_EGRESS_IP=203.0.113.7\n")
    assert load_dotenv(env_file, {}) == {
        "FIRSTOCK_USER_ID": "AB1234",
        "EXPECTED_EGRESS_IP": "203.0.113.7",
    }


def test_dotenv_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    from nifty_shop.smoke import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("# a comment\n\nFIRSTOCK_API_KEY=abc\n\n# another\n")
    assert load_dotenv(env_file, {}) == {"FIRSTOCK_API_KEY": "abc"}


def test_dotenv_strips_quotes_and_whitespace(tmp_path: Path) -> None:
    """Notepad users quote values; a quoted TOTP secret would fail authentication."""
    from nifty_shop.smoke import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text('FIRSTOCK_PASSWORD="hunter2"\nFIRSTOCK_VENDOR_CODE= AB1234_U \n')
    loaded = load_dotenv(env_file, {})
    assert loaded["FIRSTOCK_PASSWORD"] == "hunter2"
    assert loaded["FIRSTOCK_VENDOR_CODE"] == "AB1234_U"


def test_a_real_environment_variable_wins_over_the_file(tmp_path: Path) -> None:
    """An exported value is more deliberate than a file left lying around."""
    from nifty_shop.smoke import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("FIRSTOCK_USER_ID=FROM_FILE\n")
    assert load_dotenv(env_file, {"FIRSTOCK_USER_ID": "FROM_ENV"})["FIRSTOCK_USER_ID"] == "FROM_ENV"


def test_a_missing_dotenv_is_not_an_error(tmp_path: Path) -> None:
    from nifty_shop.smoke import load_dotenv

    assert load_dotenv(tmp_path / "absent", {"A": "B"}) == {"A": "B"}


def test_a_line_without_an_equals_sign_is_reported(tmp_path: Path) -> None:
    from nifty_shop.smoke import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("FIRSTOCK_USER_ID AB1234\n")
    with pytest.raises(ValueError, match="line 1"):
        load_dotenv(env_file, {})
