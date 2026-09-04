"""Read-only smoke check for the VPS.

Phase 1's gate is "read-only calls succeed on the VPS with no invented signatures".
This is how that gets tested. It logs in, reads funds and holdings, prints both with
secrets redacted, and logs out. It places no orders and has no order code path.

Run on the VPS, where the whitelisted static IP applies:

    uv run python -m nifty_shop.smoke
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from nifty_shop.broker.client import FirstockClient
from nifty_shop.broker.errors import BrokerError
from nifty_shop.preflight import (
    PreflightError,
    assert_clock_within_skew,
    assert_egress_ip,
    resolve_egress_ip,
)
from nifty_shop.redaction import redact
from nifty_shop.session import IST, SessionManager

DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"

REQUIRED_VARS = (
    "FIRSTOCK_USER_ID",
    "FIRSTOCK_PASSWORD",
    "FIRSTOCK_TOTP_SECRET",
    "FIRSTOCK_API_KEY",
    "FIRSTOCK_VENDOR_CODE",
    "EXPECTED_EGRESS_IP",
)

EGRESS_IP_URL = "https://checkip.amazonaws.com"


class MissingCredentialsError(Exception):
    """A required environment variable is absent or blank."""


def load_dotenv(path: Path, env: Mapping[str, str]) -> dict[str, str]:
    """Overlay a .env file onto the process environment.

    PowerShell has no equivalent of `source .env`, so loading it here is what makes the
    same commands work on Windows and Linux. A value already present in the real
    environment wins: exporting one is more deliberate than a file left lying around.
    """
    merged = dict(env)
    if not path.is_file():
        return merged

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path.name} line {number} has no '=': {line!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in merged:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class Credentials:
    user_id: str
    vendor_code: str
    api_key: str
    expected_egress_ip: str
    password: str = field(repr=False)
    totp_secret: str = field(repr=False)

    def totp_provider(self) -> str:
        """A fresh TOTP code. The broker rejects a reused one."""
        import pyotp

        return str(pyotp.TOTP(self.totp_secret).now())


def credentials_from_env(env: Mapping[str, str]) -> Credentials:
    """Read every credential, refusing loudly rather than defaulting."""
    missing = [name for name in REQUIRED_VARS if not env.get(name, "").strip()]
    if missing:
        raise MissingCredentialsError(
            "missing or blank environment variables: " + ", ".join(missing)
        )
    return Credentials(
        user_id=env["FIRSTOCK_USER_ID"].strip(),
        vendor_code=env["FIRSTOCK_VENDOR_CODE"].strip(),
        api_key=env["FIRSTOCK_API_KEY"].strip(),
        expected_egress_ip=env["EXPECTED_EGRESS_IP"].strip(),
        password=env["FIRSTOCK_PASSWORD"],
        totp_secret=env["FIRSTOCK_TOTP_SECRET"].strip(),
    )


def build_client(credentials: Credentials) -> FirstockClient:
    return FirstockClient(
        user_id=credentials.user_id,
        vendor_code=credentials.vendor_code,
        api_key=credentials.api_key,
    )


def _fetch_egress_ip() -> str:
    with urllib.request.urlopen(EGRESS_IP_URL, timeout=15) as response:
        return str(response.read().decode())


def run(env: Mapping[str, str], fetch_ip: Callable[[], str] = _fetch_egress_ip) -> int:
    """Return 0 on success, 1 on any refusal. Never places an order."""
    try:
        credentials = credentials_from_env(env)
    except MissingCredentialsError as exc:
        print(f"REFUSED: {exc}")
        return 1

    try:
        observed = resolve_egress_ip(fetch_ip)
        assert_egress_ip(credentials.expected_egress_ip, observed)
        print(f"preflight: egress IP {observed} matches the whitelist")

        now = datetime.now(UTC)
        assert_clock_within_skew(local=now, reference=now, max_seconds=5)
        print(f"preflight: clock {now.astimezone(IST):%Y-%m-%d %H:%M:%S %Z}")
    except PreflightError as exc:
        print(f"REFUSED: {exc}")
        return 1

    client = build_client(credentials)
    session = SessionManager(
        client=client,
        password=credentials.password,
        totp_provider=credentials.totp_provider,
        clock=lambda: datetime.now(UTC),
    )

    try:
        session.ensure_session()
        print(f"session: logged in for IST day {session.session_day}")

        print("funds:")
        print(json.dumps(redact(client.funds()), indent=2, default=str))
        print("holdings:")
        print(json.dumps(redact(client.holdings()), indent=2, default=str))
    except BrokerError as exc:
        print(f"FAILED: {exc}")
        return 1
    finally:
        if client.is_logged_in:
            client.logout()
            print("session: logged out")

    return 0


if __name__ == "__main__":
    sys.exit(run(load_dotenv(DOTENV_PATH, os.environ)))
