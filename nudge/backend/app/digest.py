"""E-mail versions of the morning briefing and evening wrap-up (simple HTML that works in Gmail)."""
from datetime import date
from html import escape

from sqlalchemy.orm import Session

from .config import get_config
from .dashboard import briefing, dashboard, wrapup
from .settings_store import Prefs

KPI_COLORS = {"Overdue": "#c62828", "Due today": "#b26a00", "Waiting on others": "#1d5fbf", "Closed this week": "#2e7d32"}


def _when(t: dict) -> str:
    bits = []
    if t.get("due_date"):
        bits.append(date.fromisoformat(t["due_date"]).strftime("%a %d %b"))
    if t.get("due_time"):
        bits.append(t["due_time"])
    if t.get("waiting_days") is not None:
        bits.append(f"waiting {t['waiting_days']}d")
    return " · ".join(bits)


def _list(title: str, items: list[dict], accent: str) -> str:
    if not items:
        return ""
    rows = "".join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #eceef2;font-size:15px;color:#1b1f27">'
        f'{escape(t["title"])}'
        + (f'<span style="color:#5b6472"> · {escape(t["person"])}</span>' if t.get("person") else "")
        + f'</td><td style="padding:8px 0 8px 12px;border-bottom:1px solid #eceef2;font-size:13px;color:#5b6472;'
        f'white-space:nowrap;text-align:right">{escape(_when(t))}</td></tr>'
        for t in items[:12]
    )
    more = (f'<p style="margin:6px 0 0;font-size:13px;color:#5b6472">and {len(items) - 12} more</p>'
            if len(items) > 12 else "")
    return (f'<h2 style="margin:24px 0 4px;font-size:13px;letter-spacing:.06em;text-transform:uppercase;'
            f'color:{accent}">{escape(title)} ({len(items)})</h2>'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{rows}</table>{more}')


def _shell(heading: str, intro: str, kpis: list[tuple[str, int]], body: str) -> str:
    url = escape(get_config().public_base_url)
    cells = "".join(
        f'<td width="25%" style="padding:12px 6px;text-align:center;background:#f6f7f9;border-radius:10px">'
        f'<div style="font-size:26px;font-weight:700;color:{KPI_COLORS.get(label, "#1b1f27")}">{n}</div>'
        f'<div style="font-size:12px;color:#5b6472">{escape(label)}</div></td>'
        for label, n in kpis
    )
    return f"""<!doctype html><html><body style="margin:0;background:#eef0f4;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:16px;padding:24px">
<tr><td>
<p style="margin:0;font-size:13px;color:#5b6472">Nudge</p>
<h1 style="margin:4px 0 8px;font-size:22px;color:#1b1f27">{escape(heading)}</h1>
<p style="margin:0 0 16px;font-size:15px;line-height:1.5;color:#2c3340">{escape(intro)}</p>
<table role="presentation" width="100%" cellspacing="6" cellpadding="0"><tr>{cells}</tr></table>
{body}
<p style="margin:28px 0 0"><a href="{url}" style="display:inline-block;background:#1d5fbf;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:10px;font-size:15px">Open Nudge</a></p>
<p style="margin:20px 0 0;font-size:12px;color:#8a93a3">You get this e-mail because the daily digest is on in Nudge settings.</p>
</td></tr></table></td></tr></table></body></html>"""


def _text_list(title: str, items: list[dict]) -> str:
    if not items:
        return ""
    lines = "\n".join(f"- {t['title']}" + (f" ({_when(t)})" if _when(t) else "") for t in items[:20])
    return f"\n\n{title}:\n{lines}"


def briefing_email(db: Session, prefs: Prefs) -> tuple[str, str, str]:
    b = briefing(db, prefs)
    k = dashboard(db, prefs)["kpis"]
    day = date.fromisoformat(b["date"]).strftime("%A %d %B")
    subject = f"Today: {len(b['due_today'])} due, {len(b['overdue'])} overdue · {day}"
    kpis = [("Overdue", k["overdue"]), ("Due today", k["due_today"]), ("Waiting on others", k["waiting"]),
            ("Closed this week", k["closed_week"])]
    body = (_list("Your Top 3", b["focus"], "#1d5fbf") + _list("Overdue", b["overdue"], "#c62828")
            + _list("Due today", b["due_today"], "#b26a00") + _list("Follow up today", b["nudges"], "#1d5fbf")
            + _list("Gone quiet: keep, reschedule or drop?", b["stale"], "#5b6472"))
    html = _shell(f"{b['greeting']}. Here's {day}.", b["text"], kpis, body)
    text = (b["text"] + _text_list("Overdue", b["overdue"]) + _text_list("Due today", b["due_today"])
            + _text_list("Follow up today", b["nudges"]) + f"\n\nOpen Nudge: {get_config().public_base_url}")
    return subject, html, text


def wrapup_email(db: Session, prefs: Prefs) -> tuple[str, str, str]:
    w = wrapup(db, prefs)
    k = dashboard(db, prefs)["kpis"]
    subject = f"Wrap-up: {len(w['closed_today'])} closed, {len(w['carried'])} carried over"
    kpis = [("Overdue", k["overdue"]), ("Due today", k["due_today"]), ("Waiting on others", k["waiting"]),
            ("Closed this week", k["closed_week"])]
    body = (_list("Closed today", w["closed_today"], "#2e7d32") + _list("Still open", w["carried"], "#c62828")
            + _list("Tomorrow", w["due_tomorrow"], "#1d5fbf"))
    html = _shell("Your day, wrapped up", w["text"], kpis, body)
    text = w["text"] + _text_list("Closed today", w["closed_today"]) + _text_list("Still open", w["carried"])
    return subject, html, text
