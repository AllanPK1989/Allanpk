"""Loads versioned prompts from backend/prompts/<name>.<version>.md.

File format: a "=== SYSTEM ===" section and a "=== USER ===" section. {{include:<file>}} pulls in a
shared fragment (without .md); {{key}} is replaced with a variable. Active versions are chosen with
the PROMPT_VERSIONS setting, so a prompt change never needs a code change.
"""
import re
from dataclasses import dataclass
from functools import lru_cache

from ..config import get_config

INCLUDE = re.compile(r"\{\{include:([\w.\-]+)\}\}")
VAR = re.compile(r"\{\{(\w+)\}\}")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    user: str

    @property
    def tag(self) -> str:
        return f"{self.name}.{self.version}"

    def render(self, variables: dict) -> tuple[str, str]:
        def fill(text: str) -> str:
            return VAR.sub(lambda m: str(variables.get(m.group(1), "")), text).strip()

        return fill(self.system), fill(self.user)


def _read(stem: str) -> str:
    path = get_config().prompts_dir / f"{stem}.md"
    text = path.read_text(encoding="utf-8")
    return INCLUDE.sub(lambda m: _read(m.group(1)).strip(), text)


@lru_cache
def load(name: str, version: str | None = None) -> Prompt:
    version = version or get_config().prompt_version(name)
    text = _read(f"{name}.{version}")
    if "=== SYSTEM ===" not in text or "=== USER ===" not in text:
        raise ValueError(f"Prompt {name}.{version} needs SYSTEM and USER sections")
    system = text.split("=== SYSTEM ===", 1)[1].split("=== USER ===", 1)[0]
    user = text.split("=== USER ===", 1)[1]
    return Prompt(name, version, system.strip(), user.strip())
