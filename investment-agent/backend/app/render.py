"""Markdown -> sanitised HTML, plus the email wrapper."""

from __future__ import annotations

import html as html_lib
import re

import markdown as md
import nh3

ALLOWED_TAGS = {"p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "h1", "h2", "h3", "h4", "table", "thead", "tbody",
                "tr", "th", "td", "a", "code", "pre", "blockquote", "hr", "span", "small", "sup", "sub", "del"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "td": {"align"}, "th": {"align"}, "span": {"class"}}


def to_html(text: str) -> str:
    raw = md.markdown(text or "", extensions=["tables", "sane_lists"])
    return nh3.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, url_schemes={"http", "https", "mailto"},
                     link_rel="noopener noreferrer nofollow")


def md_escape(s: str) -> str:
    """Escape text from outside sources (news titles) before putting it in markdown."""
    s = html_lib.escape(s or "", quote=False)
    return re.sub(r"([\\`*_\[\]|#])", r"\\\1", s)


def fmt_num(v: float | None, nd: int = 2) -> str:
    if v is None:
        return "–"
    if abs(v) >= 1e7:
        return f"{v / 1e7:,.2f} Cr"
    if abs(v) >= 1e5:
        return f"{v / 1e5:,.2f} L"
    return f"{v:,.{nd}f}"


def fmt_inr(v: float | None) -> str:
    if v is None:
        return "–"
    return ("−" if v < 0 else "") + "₹" + fmt_num(abs(v))


def fmt_pct(v: float | None) -> str:
    return "–" if v is None else f"{v:+.2f}%"


EMAIL_CSS = """
body{margin:0;background:#f3f4f6;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#111827}
.wrap{max-width:680px;margin:0 auto;padding:16px}
.card{background:#ffffff;border-radius:12px;padding:20px 22px;border:1px solid #e5e7eb}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 8px;color:#0f766e}h3{font-size:14px;margin:16px 0 6px}
p,li{font-size:14px;line-height:1.55}table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}
th,td{border-bottom:1px solid #e5e7eb;padding:6px 8px;text-align:left}th{background:#f9fafb;color:#374151}
a{color:#0f766e}.muted{color:#6b7280;font-size:12px}.btn{display:inline-block;background:#0f766e;color:#ffffff !important;
padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px}
"""


def email_html(title: str, body_html: str, *, app_url: str, footer: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html_lib.escape(title)}</title><style>{EMAIL_CSS}</style></head>
<body><div class="wrap"><div class="card"><h1>{html_lib.escape(title)}</h1>{body_html}
<p style="margin-top:22px"><a class="btn" href="{html_lib.escape(app_url)}">Open in the app</a></p>
<p class="muted">{html_lib.escape(footer)}</p></div></div></body></html>"""
