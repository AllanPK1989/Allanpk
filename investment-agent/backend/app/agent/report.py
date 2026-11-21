"""Full AI research note on one instrument."""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from .. import services
from ..data.market import MarketData
from ..models import Instrument, Report
from ..news import query as news_query
from ..render import fmt_num, md_escape, to_html
from . import llm, prompts, tools

VERDICT_RE = re.compile(r"^\s*VERDICT:\s*(.+)$", re.M)


def build(db: Session, inst: Instrument, market: MarketData) -> Report:
    settings = services.get_all_settings(db)
    analysis = tools.compact_analysis(services.analyze_instrument(inst, market=market, rf_pct=settings["risk_free_pct"]))
    data = {
        **analysis,
        "news_14d": news_query.top_for_instrument(db, inst, days=14, limit=10),
        "owner_position": tools._position(db, market, inst.symbol),
        "owner_profile": {k: settings[k] for k in ("risk_profile", "horizon_years", "tax_slab_pct", "goals_notes")},
        "today": services.now_local().strftime("%d %b %Y"),
    }
    text = llm.write(prompts.REPORT, "Instrument data:\n" + json.dumps(tools._round(data), default=str, ensure_ascii=False))
    verdict = ""
    from_ai = bool(text)
    if text:
        m = VERDICT_RE.search(text)
        if m:
            verdict = m.group(1).strip().strip("*")[:32]
            text = VERDICT_RE.sub("", text, count=1).strip()
    else:
        text = template_report(analysis)
    rep = Report(instrument_id=inst.id, verdict=verdict, markdown=text, html=to_html(text), ai_generated=from_ai)
    db.add(rep)
    db.flush()
    return rep


def template_report(a: dict) -> str:
    out = ["_AI is off (no API key), so this is a data-only summary without a verdict._", ""]
    if a.get("demo"):
        out.insert(0, "_Demo mode: the data is made up._")
    t = a.get("technical") or {}
    if t.get("stance"):
        out += ["## Technical picture", f"Stance **{t['stance']}** (score {t['score']})."]
        out += [f"- {md_escape(s)}" for s in t.get("signals", [])]
    f = a.get("fundamental") or {}
    if f.get("metrics"):
        m = f["metrics"]
        out += ["", "## Fundamentals", "| Metric | Value |", "|---|---:|"]
        for k, label in (("pe", "P/E"), ("pb", "P/B"), ("roe_pct", "ROE %"), ("net_margin_pct", "Net margin %"),
                         ("revenue_growth_pct", "Revenue growth %"), ("debt_to_equity", "Debt/equity")):
            out.append(f"| {label} | {fmt_num(m.get(k))} |")
    v = f.get("valuation") or {}
    if v.get("available"):
        fv = v["fair_value"]
        out += ["", "## Fair value (model)", f"{v['method']}: bear {fmt_num(fv['bear'])}, base {fmt_num(fv['base'])}, "
                f"bull {fmt_num(fv['bull'])}."]
    return "\n".join(out)
