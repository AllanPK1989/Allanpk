"""Telegram: the daily report on your phone, a reminder if you haven't logged in, and the
daily Firstock login by message.

Set TELEGRAM_BOT_TOKEN (from @BotFather) and TELEGRAM_CHAT_ID (your own chat) in .env.
The listener (`uv run python -m jevlab telegram`, a service on the server) answers only
your chat:
  /login 123456   log in to Firstock with the 6-digit code from your authenticator app
  /status         today's login, holdings and P&L
  /stop           kill switch: no orders until /resume
  /resume         allow orders again
"""

from __future__ import annotations

import os
import time

import requests

API = "https://api.telegram.org"


def _conf() -> tuple[str, str]:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()


def enabled() -> bool:
    token, chat = _conf()
    return bool(token and chat)


def _call(method: str, timeout: float = 15, **params):
    token, _ = _conf()
    r = requests.post(f"{API}/bot{token}/{method}", json=params, timeout=timeout)
    return r.json()


def send(text: str) -> bool:
    if not enabled():
        return False
    try:
        return bool(_call("sendMessage", chat_id=_conf()[1], text=text[:4000]).get("ok"))
    except (requests.RequestException, ValueError):
        return False


def listen() -> None:
    from . import firstock
    from .core import console
    from .shop import STOP_FILE, status_text
    if not enabled():
        raise SystemExit("  set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first")
    token, chat = _conf()
    console.print("  listening for your Telegram messages: /login 123456 · /status · /stop · /resume")
    offset = None
    while True:
        try:
            r = requests.get(f"{API}/bot{token}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=65)
            updates = r.json().get("result", [])
        except (requests.RequestException, ValueError):
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != chat:
                continue  # not you: ignore
            text = (msg.get("text") or "").strip()
            cmd, _, arg = text.partition(" ")
            cmd = cmd.lower().split("@")[0]
            if cmd == "/login":
                try:
                    _call("deleteMessage", chat_id=chat, message_id=msg.get("message_id"))  # don't leave the code lying around
                except (requests.RequestException, ValueError):
                    pass
                try:
                    s = firstock.login(arg)
                    send(f"✅ Logged in to Firstock as {s.name}. Today's shop runs at 15:18.")
                except firstock.FirstockError as exc:
                    send(f"❌ Firstock said no: {exc}. Codes change every 30 seconds: send a fresh one.")
            elif cmd == "/status":
                send(status_text())
            elif cmd == "/stop":
                STOP_FILE.touch()
                send("🛑 Kill switch on: the shop places no orders until you send /resume.")
            elif cmd == "/resume":
                STOP_FILE.unlink(missing_ok=True)
                send("▶️ Kill switch off: the shop trades again at the next 15:18 run.")
            else:
                send("Commands: /login 123456 · /status · /stop · /resume")


def whoami() -> None:
    """Print the chat ID of whoever last messaged your bot (so you can put yours in TELEGRAM_CHAT_ID)."""
    from .core import console
    token = _conf()[0]
    if not token:
        raise SystemExit("  put TELEGRAM_BOT_TOKEN in .env first")
    try:
        res = requests.get(f"{API}/bot{token}/getUpdates", timeout=15).json()
    except (requests.RequestException, ValueError):
        raise SystemExit("  couldn't reach Telegram")
    if not res.get("ok"):
        raise SystemExit("  Telegram rejected the token: check TELEGRAM_BOT_TOKEN in .env")
    chats = {}
    for u in res.get("result", []):
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("id"):
            chats[chat["id"]] = chat.get("first_name") or chat.get("username") or chat.get("title") or ""
    if not chats:
        console.print("  no messages yet: open your bot in Telegram, send it any message (say \"hi\"), then run this again")
    for cid, name in chats.items():
        console.print(f"  chat {cid} · {name}  ← put this number after TELEGRAM_CHAT_ID=")
