import json
import pathlib

import httpx
import pytest

from app.india import AmfiNavs, IndiaBook
from app.wealth import combine

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_the_statements_reconcile():
    """The CAS prints its own totals; the parse must land on them, or the whole
    India side is quietly wrong."""
    b = IndiaBook().base
    mf = [h for h in b["holdings"] if h["kind"] == "mutual_fund"]
    assert len(mf) == 28
    assert round(sum(h["value"] for h in mf), 2) == pytest.approx(1_721_783.69, abs=0.5)
    assert round(sum(h["cost"] for h in mf), 2) == pytest.approx(945_008.21, abs=0.5)

    pe = [h for h in b["holdings"] if h["kind"] == "pre_ipo"]
    assert round(sum(h["cost"] for h in pe), 2) == pytest.approx(21_483.00, abs=0.5)

    etf = [h for h in b["holdings"] if h["kind"] == "etf"]
    assert len(etf) == 8
    # broker CSV: value is qty x LTP
    n = next(h for h in etf if h["symbol"] == "NIFTYBEES")
    assert n["units"] == 1455 and n["value"] == pytest.approx(388_688.70, abs=0.5)


def test_foreign_funds_bought_in_india_are_not_counted_as_india():
    """Calling the FANG+ or China funds 'India' would understate how much of the
    book actually sits overseas."""
    b = IndiaBook().base
    by_isin = {h["isin"]: h for h in b["holdings"]}
    assert by_isin["INF769K01HH0"]["asset_class"] == "International equity"   # FANG+
    assert by_isin["INF843K01AU1"]["asset_class"] == "International equity"   # China
    assert by_isin["INF966L01986"]["asset_class"] == "India equity"           # quant ELSS


def test_an_unpriced_pre_ipo_holding_contributes_nothing_rather_than_a_guess():
    h = next(x for x in IndiaBook().base["holdings"] if x["name"] == "Sterlite Grid 5")
    assert h["unpriced"] is True
    assert h["value"] == 0 and h["cost"] == 0
    assert "no price" in h["note"].lower() or "carries no price" in h["note"]


def test_live_navs_reprice_funds_and_leave_pre_ipo_alone():
    b = IndiaBook()
    before = {h["isin"]: h["value"] for h in b.base["holdings"]}
    marked = b.mark({"INF966L01986": (500.0, "12-Sep-2026")}, {})
    rows = {(h["isin"], h["folio"]): h for h in marked["holdings"]}
    quant = [h for h in marked["holdings"] if h["isin"] == "INF966L01986"]
    assert all(h["live"] for h in quant)
    assert all(h["value"] == pytest.approx(h["units"] * 500.0, abs=0.02) for h in quant)
    pre = next(h for h in marked["holdings"] if h["kind"] == "pre_ipo")
    assert pre["live"] is False
    assert marked["totals"]["value"] != b.base["totals"]["value"]


def _amfi_with(body: str):
    """Run AmfiNavs against a canned response body."""
    import asyncio

    async def go(navs, wanted):
        transport = httpx.MockTransport(lambda r: httpx.Response(200, text=body))
        orig = httpx.AsyncClient

        class Patched(orig):
            def __init__(self, *a, **kw):
                kw["transport"] = transport
                super().__init__(*a, **kw)

        httpx.AsyncClient = Patched
        try:
            return await navs.load(wanted=wanted, wait=True)
        finally:
            httpx.AsyncClient = orig

    return go


def test_amfi_keeps_only_the_schemes_we_hold():
    """AMFI publishes every scheme in the country. Indexing all of it spiked
    memory on a small instance; an OOM restart loop reads as the site being
    down, so only the held ISINs are retained."""
    import asyncio
    header = ("Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;"
              "Scheme Name;Net Asset Value;Date\n")
    ours = "120504;INF966L01986;-;quant ELSS;460.7493;11-Sep-2026\n"
    noise = "".join(f"9{i:05d};INFZZZ{i:05d};-;Some other fund;10.0;11-Sep-2026\n"
                    for i in range(5000))
    navs = AmfiNavs()
    got = asyncio.run(_amfi_with(header + noise + ours)(navs, {"INF966L01986"}))
    assert set(got) == {"INF966L01986"}, "the whole file was indexed"
    assert got["INF966L01986"][0] == 460.7493
    assert len(got) == 1 and len(navs._navs) == 1


def test_amfi_handles_a_scheme_split_across_stream_chunks():
    """The response is streamed, so a row can straddle two chunks."""
    import asyncio
    header = ("Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;"
              "Scheme Name;Net Asset Value;Date\n")
    pad = "".join(f"9{i:05d};INFPAD{i:05d};-;Pad;10.0;11-Sep-2026\n" for i in range(3000))
    last = "120503;INF846K01K35;INF846K01K27;Axis Small Cap;137.5400;11-Sep-2026"
    navs = AmfiNavs()
    got = asyncio.run(_amfi_with(header + pad + last)(navs, {"INF846K01K35"}))
    assert got["INF846K01K35"] == (137.54, "11-Sep-2026"), "final row without a newline was lost"


def test_amfi_parses_the_published_nav_file():
    body = (
        "Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;"
        "Net Asset Value;Date\n"
        "Open Ended Schemes(Equity Scheme - Small Cap Fund)\n"
        "Axis Mutual Fund\n"
        "120503;INF846K01K35;INF846K01K27;Axis Small Cap Fund;137.5400;11-Sep-2026\n"
        "120504;INF966L01986;-;quant ELSS;460.7493;11-Sep-2026\n"
        "999999;INFBAD00001;-;Broken row;N.A.;11-Sep-2026\n")
    import asyncio
    navs = AmfiNavs()
    got = asyncio.run(_amfi_with(body)(navs, None))
    assert got["INF846K01K35"] == (137.54, "11-Sep-2026")
    assert got["INF846K01K27"] == (137.54, "11-Sep-2026")      # reinvest ISIN too
    assert got["INF966L01986"][0] == 460.7493
    assert "INFBAD00001" not in got                             # N.A. is skipped


def test_combined_totals_are_one_sum_not_two():
    us = json.loads((ROOT / "us-portfolio/data/portfolio.json").read_text())
    us["universe"] = [dict(r, live=False) for r in us["universe"]]
    ind = IndiaBook().mark({}, {})
    w = combine(us, ind, 90.0, {"source": "test"})
    assert w["totals"]["value_inr"] == pytest.approx(
        ind["totals"]["value"] + us["totals"]["value"] * 90.0, abs=1)
    assert w["totals"]["value_usd"] == pytest.approx(w["totals"]["value_inr"] / 90.0, abs=1)
    assert sum(s["share"] for s in w["sides"]) == pytest.approx(100.0, abs=0.1)
    assert sum(w["by_class"].values()) == pytest.approx(w["totals"]["value_inr"], abs=1)
    assert sum(p["weight"] for p in w["positions"]) == pytest.approx(100.0, abs=0.2)


def test_the_fx_rate_moves_the_us_side_only():
    us = json.loads((ROOT / "us-portfolio/data/portfolio.json").read_text())
    ind = IndiaBook().mark({}, {})
    lo = combine(us, ind, 80.0, {})
    hi = combine(us, ind, 100.0, {})
    india_lo = next(s for s in lo["sides"] if s["label"] == "India")
    india_hi = next(s for s in hi["sides"] if s["label"] == "India")
    assert india_lo["value_inr"] == india_hi["value_inr"]          # unchanged
    assert hi["totals"]["value_inr"] > lo["totals"]["value_inr"]   # US worth more


def test_funds_get_a_readable_label_not_an_isin():
    """The board is glanced at; a column of INF… codes is unreadable."""
    import re
    b = IndiaBook().base
    funds = [h for h in b["holdings"] if h["kind"] == "mutual_fund"]
    assert funds
    for h in funds:
        assert not re.match(r"^INF[A-Z0-9]{9}", h["symbol"]), h["symbol"]
        assert 0 < len(h["symbol"]) <= 26
        assert h["isin"].startswith(("INF", "UNCLAIM"))      # still carried for AMFI
    by = {h["symbol"] for h in funds}
    assert "Mirae Asset NYSE FANG+" in by
    assert "quant ELSS Tax Saver" in by


# ---- recommendations -------------------------------------------------------

def _called():
    from app.india_calls import annotate
    import json as _j
    us = _j.loads((ROOT / "us-portfolio/data/portfolio.json").read_text())
    return annotate(IndiaBook().mark({}, {}), us)


def test_every_holding_gets_a_call():
    b = _called()
    assert all(h.get("call") for h in b["holdings"])
    assert not [h for h in b["holdings"] if h["call"]["basis"] == "No index benchmark"], \
        "a holding fell through to no benchmark"


def test_an_unlisted_holding_gets_no_call_rather_than_a_fabricated_one():
    b = _called()
    pre = [h for h in b["holdings"] if h["kind"] == "pre_ipo"]
    assert pre and all(h["call"]["action"] == "NO CALL" for h in pre)
    assert all("no market price" in h["call"]["why"].lower() for h in pre)


def test_the_long_gilt_is_a_rate_call_not_a_value_call():
    """A gilt fund has no P/E. Into a rising cycle the long one is the exposure
    to cut, and the short one is where to sit."""
    b = _called()
    by = {h["symbol"]: h["call"] for h in b["holdings"]}
    assert by["LTGILTBEES"]["action"] == "REDUCE"
    assert by["LTGILTBEES"]["basis"] == "Rate cycle"
    assert by["LIQUIDBEES"]["action"] == "FAVOURED"
    assert by["GILT5YBEES"]["action"] == "HOLD"


def test_cheap_and_dear_indices_produce_opposite_calls():
    b = _called()
    by = {h["symbol"]: h["call"] for h in b["holdings"]}
    assert by["NIFTYBEES"]["action"] == "ADD"        # Nifty 50 below its median
    assert by["BANKBEES"]["action"] == "ADD"         # Bank Nifty below its median
    assert by["HDFCSML250"]["action"] == "PAUSE"     # smallcaps above theirs
    assert by["NIFTYBEES"]["discount"] > 0 > by["HDFCSML250"]["discount"]


def test_the_fang_feeder_is_flagged_as_duplicating_the_us_book():
    b = _called()
    fang = next(h for h in b["holdings"] if "FANG" in h["symbol"].upper())
    assert fang["call"]["action"] == "TRIM"
    assert fang["call"]["basis"] == "Duplicate exposure"


def test_elss_calls_mention_the_lock_in():
    b = _called()
    elss = [h for h in b["holdings"] if h["sub_class"] == "ELSS"]
    assert elss
    for h in elss:
        why = h["call"]["why"].lower()
        assert "three years" in why or "lock-in" in why, \
            f"the three-year lock-in is not mentioned: {h['call']['why']}"


def test_active_funds_are_not_passed_off_as_index_trackers():
    b = _called()
    active = next(h for h in b["holdings"] if h["symbol"] == "Franklin India Small Cap")
    why = active["call"]["why"].lower()
    assert why.startswith("nifty smallcap 250")        # the index frames it
    assert "active" in why, "an active fund is presented as if it tracked the index"
    # and a genuine tracker says no such thing
    tracker = next(h for h in b["holdings"] if h["symbol"] == "NIFTYBEES")
    assert "active" not in tracker["call"]["why"].lower()


def test_the_summary_totals_match_the_holdings():
    b = _called()
    total_called = sum(b["calls"]["by_action"].values())
    assert total_called == pytest.approx(b["totals"]["value"], abs=1)
