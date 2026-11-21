from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import importer, services
from ..agent import alerts as alerts_mod, digest as digest_mod, report as report_mod
from ..analysis import planning, technical
from ..config import get_settings
from ..data.market import MarketData, get_market
from ..data.types import SearchResult
from ..db import get_db
from ..models import Digest, Instrument, JobRun, PushSubscription, Report, Transaction
from ..news import collect, query as news_query, summarize
from ..notify import push
from ..security import require_owner

router = APIRouter(dependencies=[Depends(require_owner)])


def market_dep() -> MarketData:
    return get_market()


def _inst_or_404(db: Session, symbol: str) -> Instrument:
    inst = services.get_instrument(db, symbol)
    if inst is None:
        raise HTTPException(404, "Instrument not found. Search for it first.")
    return inst


# ---------- status ----------

@router.get("/status")
def status(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    s = get_settings()
    runs = {}
    for r in db.scalars(select(JobRun).order_by(JobRun.started_at.desc()).limit(50)):
        runs.setdefault(r.job, {"status": r.status, "started_at": r.started_at.isoformat(),
                                "finished_at": r.finished_at.isoformat() if r.finished_at else None})
    return {"app": s.app_name, "demo": market.demo, "ai": s.ai_enabled, "email": s.email_enabled, "push": s.push_enabled,
            "models": {"analysis": s.analysis_model, "news": s.news_model}, "jobs": runs,
            "push_subscriptions": len(list(db.scalars(select(PushSubscription.id))))}


# ---------- search & instruments ----------

@router.get("/search")
def search(q: str = Query(min_length=1, max_length=80), market: MarketData = Depends(market_dep)):
    return {"results": [r.to_dict() for r in market.search(q)]}


class FollowIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=256)
    asset_class: Literal["stock", "etf", "mutual_fund", "crypto", "index", "commodity", "forex", "bond"] = "stock"
    region: str = Field(default="GLOBAL", max_length=16)
    exchange: str = Field(default="", max_length=64)
    currency: str = Field(default="", max_length=8)
    pinned: bool = False


@router.post("/instruments")
def follow(body: FollowIn, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    """Called when the owner opens a search result: it is followed from then on."""
    r = SearchResult(symbol=body.symbol, name=body.name or body.symbol, asset_class=body.asset_class,
                     region=body.region, exchange=body.exchange, currency=body.currency)
    inst = services.follow(db, r, source="search", market=market)
    if body.pinned:
        inst.pinned = True
    return services.instrument_dict(inst)


@router.get("/instruments")
def list_followed(with_quotes: bool = True, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    insts = services.followed_instruments(db)
    quotes = market.quotes([i.symbol for i in insts]) if (insts and with_quotes) else {}
    out = []
    for i in insts:
        d = services.instrument_dict(i)
        q = quotes.get(i.symbol)
        d["quote"] = q.to_dict() if q else None
        d["held"] = bool(i.transactions)
        out.append(d)
    return {"instruments": out, "demo": market.demo}


@router.get("/instruments/{symbol:path}/analysis")
def analysis(symbol: str, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    inst = _inst_or_404(db, symbol)
    inst.last_viewed_at = services.utcnow()
    rf = services.get_all_settings(db)["risk_free_pct"]
    a = services.analyze_instrument(inst, market=market, include_chart=True, rf_pct=rf)
    a["news"] = news_query.top_for_instrument(db, inst, days=14, limit=15)
    snap = services.portfolio_snapshot(db, market=market) if inst.transactions else None
    a["position"] = next((h for h in snap["holdings"] if h["symbol"] == inst.symbol), None) if snap else None
    last = db.scalar(select(Report).where(Report.instrument_id == inst.id).order_by(Report.created_at.desc()))
    a["latest_report"] = _report_dict(last) if last else None
    return a


@router.get("/instruments/{symbol:path}/chart")
def chart(symbol: str, period: Literal["3mo", "6mo", "1y", "2y", "5y"] = "1y", market: MarketData = Depends(market_dep)):
    return technical.chart_series(market.history(symbol, period))


def _report_dict(r: Report) -> dict[str, Any]:
    return {"id": r.id, "verdict": r.verdict, "html": r.html, "ai_generated": r.ai_generated,
            "created_at": r.created_at.isoformat()}


@router.post("/instruments/{symbol:path}/report")
def make_report(symbol: str, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    inst = _inst_or_404(db, symbol)
    collect.collect(db, market, [inst], market_feeds=False, days=7)
    summarize.summarize_pending(db, limit=40)
    return _report_dict(report_mod.build(db, inst, market))


@router.post("/instruments/{symbol:path}/refresh-news")
def refresh_news(symbol: str, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    inst = _inst_or_404(db, symbol)
    stats = collect.collect(db, market, [inst], market_feeds=False, days=7)
    stats["triaged"] = summarize.summarize_pending(db, limit=40)
    return stats


class InstrumentPatch(BaseModel):
    pinned: bool | None = None
    followed: bool | None = None
    alert_pct: float | None = Field(default=None, ge=0, le=50)
    clear_alert_pct: bool = False


@router.patch("/instruments/{symbol:path}")
def patch_instrument(symbol: str, body: InstrumentPatch, db: Session = Depends(get_db)):
    inst = _inst_or_404(db, symbol)
    if body.pinned is not None:
        inst.pinned = body.pinned
    if body.followed is not None:
        inst.followed = body.followed
    if body.alert_pct is not None:
        inst.alert_pct = body.alert_pct
    if body.clear_alert_pct:
        inst.alert_pct = None
    return services.instrument_dict(inst)


@router.delete("/instruments/{symbol:path}")
def unfollow(symbol: str, db: Session = Depends(get_db)):
    inst = _inst_or_404(db, symbol)
    if inst.transactions:
        raise HTTPException(400, "You hold this instrument; delete its transactions first.")
    inst.followed = False
    inst.pinned = False
    return {"ok": True}


# ---------- market ----------

@router.get("/market/overview")
def overview(market: MarketData = Depends(market_dep)):
    return market.macro_snapshot()


# ---------- portfolio ----------

@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    return services.portfolio_snapshot(db, market=market)


@router.get("/portfolio/risk")
def portfolio_risk(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    return services.portfolio_risk(db, market=market)


@router.get("/portfolio/tax")
def portfolio_tax(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    return services.portfolio_tax(db, market=market)


@router.get("/portfolio/rebalance")
def portfolio_rebalance(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    return services.rebalance_plan(db, market=market)


class TxIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0, le=1e12)
    price: float = Field(ge=0, le=1e12)
    trade_date: date
    fees: float = Field(default=0, ge=0, le=1e9)
    fx_rate: float | None = Field(default=None, gt=0, le=1e6)
    note: str = Field(default="", max_length=256)


def _tx_dict(t: Transaction) -> dict[str, Any]:
    return {"id": t.id, "symbol": t.instrument.symbol, "name": t.instrument.name, "side": t.side, "quantity": t.quantity,
            "price": t.price, "trade_date": t.trade_date.isoformat(), "fees": t.fees, "fx_rate": t.fx_rate, "note": t.note}


@router.get("/transactions")
def list_tx(db: Session = Depends(get_db)):
    rows = db.scalars(select(Transaction).order_by(Transaction.trade_date.desc(), Transaction.id.desc()))
    return {"transactions": [_tx_dict(t) for t in rows]}


@router.post("/transactions")
def add_tx(body: TxIn, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    inst = services.resolve_symbol(db, body.symbol, market=market, source="portfolio")
    if inst is None:
        raise HTTPException(404, f"Could not find '{body.symbol}'.")
    if body.side == "sell":
        held = sum(t.quantity if t.side == "buy" else -t.quantity for t in inst.transactions)
        if body.quantity > held + 1e-9:
            raise HTTPException(400, f"You only hold {held:g} of {inst.symbol}.")
    try:
        t = services.add_transaction(db, inst, side=body.side, quantity=body.quantity, price=body.price,
                                     trade_date=body.trade_date, fees=body.fees, fx_rate=body.fx_rate, note=body.note)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _tx_dict(t)


@router.delete("/transactions/{tx_id}")
def delete_tx(tx_id: int, db: Session = Depends(get_db)):
    t = db.get(Transaction, tx_id)
    if t is None:
        raise HTTPException(404, "Not found")
    db.delete(t)
    return {"ok": True}


MAX_CSV_BYTES = 1_000_000


@router.post("/portfolio/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413, "File too large (max 1 MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    try:
        from starlette.concurrency import run_in_threadpool

        return await run_in_threadpool(importer.import_csv, db, text, market)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---------- news ----------

@router.get("/news")
def news(symbol: str | None = None, impact: Literal["high", "medium", "low"] | None = None,
         q: str | None = Query(default=None, max_length=60), days: int = Query(default=3, ge=1, le=60),
         limit: int = Query(default=60, ge=1, le=200), db: Session = Depends(get_db)):
    ids = None
    if symbol:
        inst = _inst_or_404(db, symbol)
        ids = [inst.id]
    items = news_query.recent(db, instrument_ids=ids, impact=impact, q=q, days=days, limit=limit)
    return {"news": [news_query.news_dict(n) for n in items]}


@router.post("/news/refresh")
def news_refresh(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    stats = collect.collect(db, market)
    db.commit()
    stats["triaged"] = summarize.summarize_pending(db)
    return stats


# ---------- digests & alerts ----------

@router.get("/digests")
def digests(kind: str | None = None, limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(Digest).order_by(Digest.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Digest.kind == kind)
    return {"digests": [{"id": d.id, "kind": d.kind, "title": d.title, "created_at": d.created_at.isoformat(),
                         "ai_generated": d.ai_generated, "emailed": bool(d.emailed_at), "pushed": bool(d.pushed_at)}
                        for d in db.scalars(stmt)]}


@router.get("/digests/{digest_id}")
def digest(digest_id: int, db: Session = Depends(get_db)):
    d = db.get(Digest, digest_id)
    if d is None:
        raise HTTPException(404, "Not found")
    return {"id": d.id, "kind": d.kind, "title": d.title, "html": d.html, "created_at": d.created_at.isoformat(),
            "ai_generated": d.ai_generated, "emailed": bool(d.emailed_at), "pushed": bool(d.pushed_at)}


class RunDigestIn(BaseModel):
    kind: Literal["morning", "evening", "weekly"]
    send: bool = False


@router.post("/digests/run")
def run_digest(body: RunDigestIn, db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    collect.collect(db, market, days=7 if body.kind == "weekly" else 2)
    db.commit()
    summarize.summarize_pending(db)
    d = digest_mod.build(db, body.kind, market)
    sent = digest_mod.deliver(db, d) if body.send else {}
    return {"id": d.id, "title": d.title, **sent}


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    return {"alerts": alerts_mod.recent_alerts(db)}


@router.post("/alerts/check")
def alerts_check(db: Session = Depends(get_db), market: MarketData = Depends(market_dep)):
    found = alerts_mod.check(db, market)
    sent = alerts_mod.deliver(db, found)
    return {"new": [a.title for a in found], **sent}


# ---------- planning ----------

class GoalIn(BaseModel):
    target_amount_today: float = Field(gt=0, le=1e13)
    years: float = Field(gt=0, le=60)
    inflation_pct: float = Field(default=6.0, ge=0, le=20)
    expected_return_pct: float = Field(default=11.0, ge=0, le=30)
    current_savings: float = Field(default=0, ge=0, le=1e13)
    step_up_pct: float = Field(default=0, ge=0, le=50)


@router.post("/plan/goal")
def plan_goal(body: GoalIn):
    return planning.goal_plan(target_today=body.target_amount_today, years=body.years, inflation_pct=body.inflation_pct,
                              expected_return_pct=body.expected_return_pct, current_savings=body.current_savings,
                              step_up_pct=body.step_up_pct)


class RetireIn(BaseModel):
    current_age: int = Field(ge=15, le=90)
    retire_age: int = Field(ge=20, le=90)
    life_expectancy: int = Field(default=85, ge=50, le=110)
    monthly_expense_today: float = Field(gt=0, le=1e10)
    inflation_pct: float = Field(default=6.0, ge=0, le=20)
    pre_return_pct: float = Field(default=11.0, ge=0, le=30)
    post_return_pct: float = Field(default=7.5, ge=0, le=20)
    current_corpus: float = Field(default=0, ge=0, le=1e13)
    step_up_pct: float = Field(default=10.0, ge=0, le=50)


@router.post("/plan/retirement")
def plan_retirement(body: RetireIn):
    if body.retire_age <= body.current_age or body.life_expectancy <= body.retire_age:
        raise HTTPException(400, "Ages must be in order: current < retirement < life expectancy.")
    return planning.retirement_plan(**body.model_dump())


# ---------- settings ----------

class SettingsIn(BaseModel):
    risk_profile: Literal["conservative", "moderate", "aggressive"] | None = None
    horizon_years: int | None = Field(default=None, ge=1, le=60)
    age: int | None = Field(default=None, ge=15, le=100)
    tax_slab_pct: float | None = Field(default=None, ge=0, le=42.744)
    ltcg_exemption_used: float | None = Field(default=None, ge=0, le=1e9)
    risk_free_pct: float | None = Field(default=None, ge=0, le=20)
    rbi_repo_rate_pct: float | None = Field(default=None, ge=0, le=20)
    alert_pct: float | None = Field(default=None, gt=0, le=50)
    alert_pct_crypto: float | None = Field(default=None, gt=0, le=80)
    email_digests: bool | None = None
    email_alerts: bool | None = None
    push_digests: bool | None = None
    push_alerts: bool | None = None
    digests_enabled: dict[Literal["morning", "evening", "weekly"], bool] | None = None
    goals_notes: str | None = Field(default=None, max_length=2000)


@router.get("/settings")
def get_settings_route(db: Session = Depends(get_db)):
    return services.get_all_settings(db)


@router.put("/settings")
def put_settings(body: SettingsIn, db: Session = Depends(get_db)):
    return services.update_settings(db, body.model_dump(exclude_unset=True))


# ---------- push ----------

@router.get("/push/public-key")
def push_key():
    s = get_settings()
    return {"enabled": s.push_enabled, "public_key": s.vapid_public_key}


class SubKeys(BaseModel):
    p256dh: str = Field(min_length=10, max_length=256)
    auth: str = Field(min_length=4, max_length=128)


class SubIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000, pattern=r"^https://")
    keys: SubKeys
    user_agent: str = Field(default="", max_length=256)


@router.post("/push/subscribe")
def push_subscribe(body: SubIn, db: Session = Depends(get_db)):
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        db.add(PushSubscription(endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth,
                                user_agent=body.user_agent))
    else:
        sub.p256dh, sub.auth = body.keys.p256dh, body.keys.auth
    return {"ok": True}


class UnsubIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)


@router.post("/push/unsubscribe")
def push_unsubscribe(body: UnsubIn, db: Session = Depends(get_db)):
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub:
        db.delete(sub)
    return {"ok": True}


@router.post("/push/test")
def push_test(db: Session = Depends(get_db)):
    return {"sent": push.send_all(db, title="Test notification", body="Push notifications are working.", url="/")}
