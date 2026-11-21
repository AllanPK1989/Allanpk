"""The advisor chat: a streamed tool-use loop with Claude.

History is append-only and stored exactly as the API returned it (thinking blocks included), so every
request replays earlier turns unchanged.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from .. import services
from ..config import get_settings
from ..data.market import MarketData
from ..models import ChatMessage, ChatSession, utcnow
from . import llm, prompts, tools

log = logging.getLogger(__name__)
MAX_STEPS = 14


def _system(db: Session, market: MarketData) -> list[dict[str, Any]]:
    settings = services.get_all_settings(db)
    today = services.now_local().strftime("%A %d %B %Y, %H:%M")
    return [
        {"type": "text", "text": prompts.ADVISOR, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": prompts.owner_context(settings, today=today, data_mode="demo" if market.demo else "live")},
    ]


def _save(db: Session, session: ChatSession, role: str, content: list[dict[str, Any]]) -> None:
    session.messages.append(ChatMessage(role=role, content=content))
    session.updated_at = utcnow()
    db.commit()


def history(session: ChatSession) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in session.messages]


def run_turn(db: Session, session: ChatSession, user_text: str, market: MarketData) -> Iterator[dict[str, Any]]:
    """Yields UI events: {"type": "text"|"tool"|"tool_done"|"done"|"error", ...}."""
    user_text = user_text.strip()[:8000]
    if session.title == "New chat":
        session.title = user_text[:60] + ("…" if len(user_text) > 60 else "")
    _save(db, session, "user", [{"type": "text", "text": user_text}])

    if not llm.ai_enabled():
        yield from _offline_reply(db, session, user_text, market)
        return

    s = get_settings()
    messages = history(session)
    system = _system(db, market)
    json_retries = 0
    for _step in range(MAX_STEPS):
        try:
            with llm.client().beta.messages.stream(
                model=s.analysis_model,
                max_tokens=32000,
                system=system,
                tools=tools.TOOLS,
                messages=messages,
                output_config={"effort": s.chat_effort},
                cache_control={"type": "ephemeral"},
                **llm.fallback_kwargs(s.analysis_model),
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        yield {"type": "text", "text": event.text}
                msg = stream.get_final_message()
            json_retries = 0
        except ValueError:
            # Tool input JSON the SDK could not parse at all: re-issue the turn (bounded).
            json_retries += 1
            if json_retries > 2:
                yield {"type": "error", "message": "The model produced an unreadable tool call. Please try again."}
                return
            continue
        except anthropic.RateLimitError:
            yield {"type": "error", "message": "Claude is rate limited right now. Try again in a minute."}
            return
        except anthropic.APIStatusError as e:
            log.error("chat API error %s: %s", e.status_code, e.message)
            yield {"type": "error", "message": f"Claude API error ({e.status_code})."}
            return
        except anthropic.APIConnectionError:
            yield {"type": "error", "message": "Could not reach Claude. Check the network and try again."}
            return

        if msg.stop_reason == "refusal":
            # Nothing is saved for a declined turn, so history stays valid.
            yield {"type": "error", "message": "The model declined to answer this request."}
            return

        content = [b.to_dict(mode="json") for b in msg.content]
        _save(db, session, "assistant", content)
        messages.append({"role": "assistant", "content": content})

        if msg.stop_reason == "pause_turn":
            continue
        tool_uses = [b for b in msg.content if b.type == "tool_use"]
        if not tool_uses:
            yield {"type": "done"}
            return
        if msg.stop_reason == "max_tokens":
            yield {"type": "error", "message": "The reply was cut off (too long). Ask for a shorter answer."}
            return

        results = []
        for tu in tool_uses:
            yield {"type": "tool", "id": tu.id, "name": tu.name, "input": tu.input}
            out, is_error = tools.execute(db, market, tu.name, tu.input)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out, **({"is_error": True} if is_error else {})})
            yield {"type": "tool_done", "id": tu.id, "name": tu.name, "error": is_error}
        _save(db, session, "user", results)
        messages.append({"role": "user", "content": results})
    yield {"type": "error", "message": "Stopped after too many tool steps. Ask a narrower question."}


def _offline_reply(db: Session, session: ChatSession, text: str, market: MarketData) -> Iterator[dict[str, Any]]:
    """Without an API key: say so, and still show a data-only analysis if the message names an instrument."""
    parts = ["**AI is off** (no `ANTHROPIC_API_KEY` set), so I can't reason about your question. "
             "Here is what the data tools return without AI.\n"]
    results = market.search(text[:60]) if len(text) <= 60 else []
    if results:
        inst = services.follow(db, results[0], source="agent", market=market)
        a = services.analyze_instrument(inst, market=market)
        t, q = a["technical"], a["quote"]
        parts.append(f"### {inst.name} ({inst.symbol})\n")
        if q.get("price") is not None:
            chg = q.get("change_pct")
            parts.append(f"Price {q['price']:,.2f} {q.get('currency') or ''}" + (f" ({chg:+.2f}% today)" if chg is not None else "") + "\n")
        if t.get("available"):
            parts.append(f"Technical stance: **{t['stance']}** (score {t['score']})\n")
            parts += [f"- {s['text']}" for s in t["signals"]]
            parts.append("")
        fv = (a["fundamental"].get("valuation") or {}).get("fair_value") if a["fundamental"].get("available") else None
        if fv:
            parts.append(f"Model fair value: bear {fv['bear']:,} / base {fv['base']:,} / bull {fv['bull']:,}")
        parts.append("\nI've added it to your followed list, so its news will appear in your digests.")
    else:
        parts.append("Type a company, fund or coin name to see its data, or add an API key in the settings to chat.")
    reply = "\n".join(parts)
    _save(db, session, "assistant", [{"type": "text", "text": reply}])
    yield {"type": "text", "text": reply}
    yield {"type": "done"}


def display_messages(session: ChatSession) -> list[dict[str, Any]]:
    """Turn stored API messages into what the chat UI shows: user text, assistant text and tool chips."""
    out: list[dict[str, Any]] = []
    for m in session.messages:
        texts = [b.get("text", "") for b in m.content if b.get("type") == "text"]
        tool_calls = [{"name": b.get("name"), "input": b.get("input")} for b in m.content if b.get("type") == "tool_use"]
        if m.role == "user" and texts:
            out.append({"role": "user", "text": "\n".join(texts), "at": m.created_at.isoformat()})
        elif m.role == "assistant":
            if out and out[-1]["role"] == "assistant":
                prev = out[-1]
                prev["text"] = (prev["text"] + "\n\n" + "\n".join(texts)).strip() if texts else prev["text"]
                prev["tools"] += tool_calls
            else:
                out.append({"role": "assistant", "text": "\n".join(texts), "tools": tool_calls, "at": m.created_at.isoformat()})
    return out
