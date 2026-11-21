"""One shared HTTP client for the keyless data sources."""

from __future__ import annotations

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; InvestmentAnalyst/1.0; personal use)"

_client: httpx.Client | None = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10),
        )
    return _client


def set_client(c: httpx.Client | None) -> None:
    """Tests inject a client with a mock transport."""
    global _client
    _client = c
