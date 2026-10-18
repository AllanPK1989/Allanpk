"""Paths and YAML loading shared by every pipeline step.

The repo runs more than one YouTube channel from the same curriculum. Each
channel is a profile: `config.yaml` is the Tamil channel (and the base every
other profile starts from), and `channels/<id>.yaml` overrides it, e.g.
`channels/en.yaml` for the English channel. The active channel comes from the
FINANCE_CHANNEL environment variable (`python -m pipeline --channel en ...`
sets it); the default is `ta`.
"""
from __future__ import annotations

import contextlib
import functools
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"          # Tamil scripts: the source every channel's script comes from
CHANNELS = ROOT / "channels"
CACHE = ROOT / ".cache"
TEMPLATES = Path(__file__).resolve().parent / "templates"
MUSIC = ROOT / "assets" / "music"
DEFAULT_CHANNEL = "ta"

# Sections a channel profile merges into config.yaml key by key; every other
# section in a profile replaces the base section as a whole.
MERGED_SECTIONS = {"channel", "voice", "video", "publish", "recording"}


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def channel_id() -> str:
    return os.environ.get("FINANCE_CHANNEL") or DEFAULT_CHANNEL


@contextlib.contextmanager
def using_channel(ch: str):
    """Temporarily switch the active channel (e.g. to write the Tamil source script)."""
    old = os.environ.get("FINANCE_CHANNEL")
    os.environ["FINANCE_CHANNEL"] = ch
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("FINANCE_CHANNEL", None)
        else:
            os.environ["FINANCE_CHANNEL"] = old


def channel_ids() -> list[str]:
    return [DEFAULT_CHANNEL] + sorted(p.stem for p in CHANNELS.glob("*.yaml") if p.stem != DEFAULT_CHANNEL)


@functools.cache
def _config(ch: str) -> dict:
    cfg = load_yaml(ROOT / "config.yaml")
    if ch != DEFAULT_CHANNEL:
        p = CHANNELS / f"{ch}.yaml"
        if not p.exists():
            raise FileNotFoundError(f"unknown channel {ch!r}: no {p.relative_to(ROOT)}")
        for k, v in (load_yaml(p) or {}).items():
            if k in MERGED_SECTIONS and isinstance(v, dict):
                cfg[k] = {**(cfg.get(k) or {}), **v}
            else:
                cfg[k] = v
    cfg["channel"].setdefault("id", ch)
    return cfg


def config() -> dict:
    return _config(channel_id())


def lang() -> str:
    return config()["channel"].get("language", "ta")


def loc(section: dict, key: str, default=None):
    """`key_<lang>` from a config section (e.g. screen_ta / screen_en), else plain `key`."""
    return section.get(f"{key}_{lang()}", section.get(key, default))


def strings() -> dict:
    """Fixed wording the pipeline adds itself (CTAs, labels, description lines)."""
    return config()["strings"]


def content_dir() -> Path:
    return ROOT / config()["channel"].get("content_dir", "content")


def state_dir() -> Path:
    return ROOT / config()["channel"].get("state_dir", "state/items")


def release_tag(topic_id: str) -> str:
    return f"{config()['channel'].get('release_prefix', 'video-')}{str(topic_id).zfill(3)}"


@functools.cache
def categories() -> dict:
    return load_yaml(ROOT / "categories.yaml")


@functools.cache
def curriculum() -> list[dict]:
    return load_yaml(ROOT / "curriculum.yaml")["topics"]


def accent_soft(hex_color: str, alpha: float = 0.16) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
