"""Shared bits: where results go, the terminal styling, India time, and rupees."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich import box
from rich.console import Console
from rich.panel import Panel

RESULTS = Path(__file__).resolve().parent.parent / "results"
console = Console(highlight=False)

IST = ZoneInfo("Asia/Kolkata")


def header(title: str, subtitle: str) -> None:
    console.print()
    console.print(Panel(f"[dim]{subtitle}[/]", title=f"[bold #8b7bff]{title}[/]", title_align="left",
                        border_style="#3a3f5c", box=box.ROUNDED, padding=(0, 2)))


def ist_now() -> datetime:
    return datetime.now(IST)


def inr(v: float, sign: bool = False) -> str:
    """Rupees with Indian digit grouping: 1234567.8 -> ₹12,34,567.80"""
    neg, v = v < 0, abs(v)
    whole, paise = f"{v:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(([head] if head else []) + groups + [tail])
    return ("-" if neg else "+" if sign else "") + f"₹{whole}.{paise}"
