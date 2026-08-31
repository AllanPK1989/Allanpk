"""Redaction of secrets before anything is logged or persisted.

Prime directive: never log tokens, keys or session IDs, including in traces. Every
audit record and every log line passes through redact() first.
"""

from __future__ import annotations

from typing import Final

REDACTED: Final = "***REDACTED***"

#: Matched case-insensitively against dictionary keys. The API mixes casing
#: (jKey, TOTP, apiKey), so exact-case matching would leak.
SECRET_KEYS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "pwd",
        "totp",
        "factor2",
        "apikey",
        "appkey",
        "vendorcode",
        "jkey",
        "susertoken",
        "token",
        "secret",
        "authorization",
    }
)


def redact(value: object) -> object:
    """Return a copy of value with every secret-looking field replaced.

    Recurses through mappings and sequences. Non-secret values pass through unchanged.
    """
    if isinstance(value, dict):
        return {
            key: REDACTED if str(key).lower() in SECRET_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value
