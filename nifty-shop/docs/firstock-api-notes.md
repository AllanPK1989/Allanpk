# Firstock API — what is verified, and what is not

**Date:** 2026-08-31 · **Source:** `firstock` 1.1.11 sdist from PyPI
(`the-firstock/firstock-developer-sdk-python`), read directly from source.

`https://firstock.in/api/docs/` is denied by this environment's egress policy (403 on
CONNECT), so the documentation site could not be read. Everything below is taken from
the SDK's own code. **Nothing here is inferred or invented.** Items under "Not
determinable" are escalated rather than guessed, per the spec.

## Verified — request side

Base: `https://api.firstock.in/V1/`. All calls are `POST` with a JSON body.

| Call | Path | Body |
|---|---|---|
| Login | `/login` | `userId`, `password` (**SHA-256 hex of the plaintext**), `TOTP`, `vendorCode`, `apiKey` |
| Logout | `/logout` | `userId`, `jKey` |
| Funds | `/limit` | `userId`, `actid`, `jKey` |
| Holdings | `/holdings` | `userId`, `actid`, `product` (`"C"` for CNC), `jKey` |

`actid` is passed the same value as `userId` throughout the SDK. The session token is
returned as `data.susertoken` and is sent back on every later call as `jKey`.

## Verified — response envelope

Responses carry a `status` field and a `data` object. Login success is
`data.susertoken`.

## Not determinable from the SDK — escalated, not guessed

1. **Field names inside `holdings` and `limit` responses.** The README shows request
   examples only, with no sample responses. Whether `holdings` returns a list or an
   object is also unknown. The client therefore validates the envelope and returns the
   raw `data` payload; mapping it to domain types waits for one real response.
2. **Error codes and their meanings.** `Variables/error_list.py` contains only two
   client-side stubs (`not_valid_user`, `not_logged_in_user`). There is no server error
   catalogue in the package.
3. **Rate limits.** Nothing in the package states them. The token bucket defaults to the
   spec's 2 orders/sec, which is a self-imposed ceiling, not a documented one.
4. **Session lifetime.** The spec assumes one session per trading day. The SDK stores a
   token indefinitely and never expires it.

## Defects in the SDK — reasons this project does not call it

The SDK is used as a **specification of the wire format only**. A thin typed client is
written instead, because:

1. **Errors are swallowed and become `None`.** `holdings` and `limit` end in
   `except Exception as e: print(e)`, with no return. A failed holdings call returns
   `None`, which a caller can easily read as "no holdings". For a system whose exit
   decisions depend on holdings, that is the worst possible failure mode. The spec's
   "fail closed" and "no swallowed exceptions" rules both forbid it.
2. **Responses are parsed with `ast.literal_eval`, not `json.loads`.** Besides being the
   wrong tool for server-controlled input, it cannot parse JSON `true`, `false` or
   `null` at all — those raise `ValueError`.
3. **`status` is compared inconsistently**: login tests `== "success"`, logout tests
   `== "Success"`. Our client compares case-insensitively and treats anything that is
   not an explicit success as a failure.
4. **The session token is written to a `config.json` on disk** by the library. This
   project holds the token in memory only and never writes it to the repository tree.

## Open question for the account owner

Confirm the **rate limits** and the **error-code list** from the docs site or your
account dashboard, and provide **one real `holdings` and one real `limit` response**
(redacted) so the domain mapping can be written against fact rather than assumption.
