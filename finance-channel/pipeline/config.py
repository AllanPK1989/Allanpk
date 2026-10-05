"""Paths and YAML loading shared by every pipeline step."""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
STATE_DIR = ROOT / "state" / "items"
CACHE = ROOT / ".cache"
TEMPLATES = Path(__file__).resolve().parent / "templates"
MUSIC = ROOT / "assets" / "music"


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@functools.cache
def config() -> dict:
    return load_yaml(ROOT / "config.yaml")


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
