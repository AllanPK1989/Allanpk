"""Write new Tamil scripts with Claude for curriculum topics that have none.

Tamil is the source language for every channel, so this always writes to
content/ (other channels translate from it; see translate.py).

Needs ANTHROPIC_API_KEY. Every generated script must pass the same lint
(structure + compliance) as hand-written ones; if it doesn't, the errors are
sent back to Claude for a fix, up to MAX_FIXES times. You still approve the
rendered video before anything is published.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from .compliance import lint
from .config import CONTENT, DEFAULT_CHANNEL, ROOT, categories, curriculum, using_channel
from .script import Script, all_scripts, find_script

MODEL = "claude-opus-5-5"
MAX_FIXES = 2
EXAMPLES = ["001", "002"]  # hand-written scripts shown to the model as reference


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _system_prompt() -> str:
    guide = (ROOT / "docs" / "WRITING_GUIDE.md").read_text(encoding="utf-8")
    examples = []
    for tid in EXAMPLES:
        p = find_script(tid, CONTENT)
        if p:
            examples.append(f"<example file=\"{p.name}\">\n{p.read_text(encoding='utf-8')}\n</example>")
    cats = yaml.safe_dump(categories(), allow_unicode=True, sort_keys=False)
    return (
        "You write scripts for “நிதி அறிவு”, a Tamil YouTube channel that teaches personal finance "
        "and investing basics to Indian beginners, one concept per video. The channel owner is not a "
        "SEBI-registered adviser, so every script is strictly educational.\n\n"
        "Follow this writing guide exactly; it also defines the YAML format.\n\n"
        f"<writing_guide>\n{guide}\n</writing_guide>\n\n"
        f"<categories>\n{cats}</categories>\n\n"
        "Reference scripts written by the channel (match their tone, depth, pacing and YAML shape):\n\n"
        + "\n\n".join(examples)
        + "\n\nAccuracy matters more than anything else: explain only facts you are confident are correct "
        "for India. When a rule or rate changes often, explain the mechanism and say viewers should check "
        "the current figure on the official website. All numbers in examples are round, hypothetical and "
        "labelled as examples.\n\n"
        "Reply with the complete script as a single ```yaml fenced block and nothing else."
    )


def _user_prompt(topic: dict, done: list[str]) -> str:
    cat = categories()[topic["category"]]
    lines = [
        f"Write the script for topic {str(topic['id']).zfill(3)}.",
        f"- category: {topic['category']} ({cat['en']} / {cat['ta']})",
        f"- English title: {topic['title_en']}",
        f"- Tamil title: {topic.get('title_ta', '(write one)')}",
    ]
    if topic.get("notes"):
        lines.append(f"- What to cover: {topic['notes']}")
    if done:
        lines.append("\nEarlier videos in the series (you may refer back to them; don't repeat them):")
        lines += [f"- {t}" for t in done[-40:]]
    return "\n".join(lines)


def _extract_yaml(text: str) -> str:
    m = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"


def _call(client, system: str, messages: list[dict]):
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude declined to write this script; write it by hand")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("script generation ran out of tokens")
    return msg


def generate(topic_id: str) -> Path:
    with using_channel(DEFAULT_CHANNEL):
        return _generate(topic_id)


def _generate(topic_id: str) -> Path:
    import anthropic

    tid = str(topic_id).zfill(3)
    topic = next((t for t in curriculum() if str(t["id"]).zfill(3) == tid), None)
    if topic is None:
        raise KeyError(f"topic {tid} is not in curriculum.yaml")
    if find_script(tid, CONTENT):
        raise FileExistsError(f"topic {tid} already has a script")
    done = [f"{s.id}: {s['title_ta']} ({s['title_en']})" for s in all_scripts() if s.id < tid]
    client = anthropic.Anthropic()
    system = _system_prompt()
    messages: list[dict] = [{"role": "user", "content": _user_prompt(topic, done)}]
    out = CONTENT / f"{tid}-{topic['slug']}.yaml"

    for attempt in range(MAX_FIXES + 1):
        msg = _call(client, system, messages)
        text = _extract_yaml("".join(b.text for b in msg.content if b.type == "text"))
        problems: list[str] = []
        try:
            data = yaml.safe_load(text)
            if not isinstance(data, dict):
                raise ValueError("the reply is not a YAML mapping")
            data["id"] = tid
            data["category"] = topic["category"]
            rep = lint(Script(out, data))
            problems = rep.errors
        except Exception as e:  # noqa: BLE001 - YAML/shape errors go back to the model
            problems = [f"could not parse the YAML: {e}"]
        if not problems:
            body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
            out.write_text(f"# Generated by Claude ({MODEL}); review before approving.\n" + body, encoding="utf-8")
            return out
        if attempt == MAX_FIXES:
            break
        messages += [
            {"role": "assistant", "content": msg.content},  # full blocks: history stays append-only
            {"role": "user", "content": "The script failed validation. Fix every problem below and reply "
                                        "with the full corrected script:\n" + "\n".join(f"- {p}" for p in problems)},
        ]
    raise RuntimeError(f"generated script for {tid} still fails validation:\n" + "\n".join(problems))
