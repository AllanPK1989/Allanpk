from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from nifty_shop.broker.client import FirstockClient, sha256_hex
from nifty_shop.broker.errors import (
    BrokerAuthError,
    BrokerResponseError,
    BrokerTransportError,
    NotLoggedInError,
)
from nifty_shop.broker.transport import HttpResponse


class RecordingTransport:
    """Fake transport. Records calls; returns canned responses. No network."""

    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, Mapping[str, object]]] = []
        self.timeouts: list[float] = []

    def post(self, url: str, payload: Mapping[str, object], timeout: float) -> HttpResponse:
        self.calls.append((url, dict(payload)))
        self.timeouts.append(timeout)
        if not self._responses:
            raise AssertionError("fake transport ran out of canned responses")
        return self._responses.pop(0)


def ok(body: object) -> HttpResponse:
    return HttpResponse(status_code=200, text=json.dumps(body))


def login_ok() -> HttpResponse:
    return ok({"status": "success", "data": {"susertoken": "tok-123"}})


def make_client(transport: RecordingTransport) -> FirstockClient:
    return FirstockClient(
        user_id="AB1234",
        vendor_code="AB1234_U",
        api_key="key",
        transport=transport,
    )


def test_password_is_sha256_hexed_and_plaintext_never_sent() -> None:
    transport = RecordingTransport([login_ok()])
    client = make_client(transport)
    client.login(password="hunter2", totp="123456")

    _, payload = transport.calls[0]
    assert payload["password"] == sha256_hex("hunter2")
    assert "hunter2" not in json.dumps(payload)


def test_login_posts_the_documented_fields() -> None:
    transport = RecordingTransport([login_ok()])
    client = make_client(transport)
    client.login(password="p", totp="654321")

    url, payload = transport.calls[0]
    assert url == "https://api.firstock.in/V1/login"
    assert set(payload) == {"userId", "password", "TOTP", "vendorCode", "apiKey"}
    assert payload["userId"] == "AB1234"
    assert payload["TOTP"] == "654321"
    assert payload["vendorCode"] == "AB1234_U"


def test_calls_before_login_refuse_rather_than_returning_empty() -> None:
    """The SDK returns None here; an empty holdings list would be catastrophic."""
    client = make_client(RecordingTransport([]))
    with pytest.raises(NotLoggedInError):
        client.holdings()
    with pytest.raises(NotLoggedInError):
        client.funds()


def test_holdings_sends_the_session_token_and_cnc_product() -> None:
    transport = RecordingTransport([login_ok(), ok({"status": "success", "data": []})])
    client = make_client(transport)
    client.login(password="p", totp="1")
    client.holdings()

    url, payload = transport.calls[1]
    assert url == "https://api.firstock.in/V1/holdings"
    assert payload == {"userId": "AB1234", "actid": "AB1234", "product": "C", "jKey": "tok-123"}


def test_funds_sends_the_session_token() -> None:
    transport = RecordingTransport([login_ok(), ok({"status": "success", "data": {"cash": "1"}})])
    client = make_client(transport)
    client.login(password="p", totp="1")
    assert client.funds() == {"cash": "1"}
    assert transport.calls[1][1] == {"userId": "AB1234", "actid": "AB1234", "jKey": "tok-123"}


def test_status_comparison_is_case_insensitive() -> None:
    """The SDK checks 'success' on login but 'Success' on logout; we accept both."""
    transport = RecordingTransport([ok({"status": "Success", "data": {"susertoken": "t"}})])
    client = make_client(transport)
    client.login(password="p", totp="1")
    assert client.is_logged_in is True


def test_a_failed_status_raises_and_does_not_return_data() -> None:
    transport = RecordingTransport([ok({"status": "Failed", "message": "invalid TOTP"})])
    client = make_client(transport)
    with pytest.raises(BrokerAuthError, match="invalid TOTP"):
        client.login(password="p", totp="000000")


def test_non_200_raises() -> None:
    transport = RecordingTransport([HttpResponse(status_code=503, text="upstream down")])
    client = make_client(transport)
    with pytest.raises(BrokerTransportError, match="503"):
        client.login(password="p", totp="1")


def test_unparseable_body_raises_rather_than_being_evaluated() -> None:
    """The SDK uses ast.literal_eval here, which cannot even parse JSON true/false."""
    transport = RecordingTransport([HttpResponse(status_code=200, text="<html>oops</html>")])
    client = make_client(transport)
    with pytest.raises(BrokerResponseError):
        client.login(password="p", totp="1")


def test_json_booleans_and_nulls_parse_fine() -> None:
    body = {"status": "success", "data": {"susertoken": "t", "active": True, "note": None}}
    transport = RecordingTransport([ok(body)])
    client = make_client(transport)
    client.login(password="p", totp="1")
    assert client.is_logged_in is True


def test_a_success_response_missing_the_token_fails_closed() -> None:
    transport = RecordingTransport([ok({"status": "success", "data": {}})])
    client = make_client(transport)
    with pytest.raises(BrokerResponseError, match="susertoken"):
        client.login(password="p", totp="1")


def test_logout_clears_the_session() -> None:
    transport = RecordingTransport([login_ok(), ok({"status": "Success", "data": {}})])
    client = make_client(transport)
    client.login(password="p", totp="1")
    client.logout()
    assert client.is_logged_in is False
    with pytest.raises(NotLoggedInError):
        client.holdings()


def test_repr_never_leaks_the_session_token() -> None:
    transport = RecordingTransport([login_ok()])
    client = make_client(transport)
    client.login(password="p", totp="1")
    assert "tok-123" not in repr(client)


def test_every_request_carries_a_positive_timeout() -> None:
    """An unbounded request would hang the daily job past 15:30."""
    transport = RecordingTransport([login_ok(), ok({"status": "success", "data": []})])
    client = make_client(transport)
    client.login(password="p", totp="1")
    client.holdings()
    assert transport.timeouts
    assert all(t > 0 for t in transport.timeouts)
