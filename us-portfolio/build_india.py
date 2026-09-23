#!/usr/bin/env python3
"""Build the India side of the book from the three source documents.

Sources, all dated 14 Sep 2026
  data/sources/mf_cas_rows.json   parsed from the CAMS/KFintech CAS
  data/sources/zerodha_holdings.csv  broker holdings export
  pre-IPO rows below, transcribed from the PE holding statement

Run:  python3 build_india.py  ->  data/india.json
"""
import csv, json, pathlib, re

HERE = pathlib.Path(__file__).parent
AS_OF = "2026-09-14"

# ---------------------------------------------------------------- classification
# Several "Indian" funds hold foreign equity. Counting them as India would
# understate how much of the book is really overseas, so they are tagged by
# what they own, not where they are bought.
INTERNATIONAL_ISINS = {
    "INF769K01HH0": "US tech (FANG+)",
    "INF843K01AU1": "China equity",
    "INF740KA1QP1": "Global innovation",
    "INF205KA1270": "Global consumer",
    "INF740K01OZ9": "Global gold miners",
}
DEBT_ISINS = {"UNCLAIMDISIN"}

def classify_fund(name, isin):
    if isin in INTERNATIONAL_ISINS:
        return "International equity", INTERNATIONAL_ISINS[isin]
    if isin in DEBT_ISINS or "overnight" in name.lower() or "liquid" in name.lower():
        return "Debt / cash", "Overnight"
    n = name.lower()
    if "small cap" in n:   return "India equity", "Small cap"
    if "midcap" in n or "mid cap" in n: return "India equity", "Mid cap"
    if "elss" in n or "tax saver" in n: return "India equity", "ELSS"
    if "bank" in n:        return "India equity", "Banking"
    if "digital" in n:     return "India equity", "Technology"
    if "next 50" in n:     return "India equity", "Large cap index"
    if "nifty 50" in n or "index" in n: return "India equity", "Large cap index"
    return "India equity", "Diversified"

ETF_META = {
    "NIFTYBEES":  ("Nippon India ETF Nifty 50 BeES", "India equity", "Large cap index", "INF204KB14I2"),
    "JUNIORBEES": ("Nippon India ETF Nifty Next 50 Junior BeES", "India equity", "Large cap index", "INF732E01045"),
    "BANKBEES":   ("Nippon India ETF Nifty Bank BeES", "India equity", "Banking", "INF732E01037"),
    "MIDCAPETF":  ("Motilal Oswal Nifty Midcap 150 ETF", "India equity", "Mid cap", "INF247L01AP3"),
    "HDFCSML250": ("HDFC Nifty Smallcap 250 ETF", "India equity", "Small cap", "INF179KC1AP7"),
    "LTGILTBEES": ("Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt", "Debt / cash", "Long gilt", "INF204KB17I5"),
    "GILT5YBEES": ("Nippon India ETF Nifty 5 yr Benchmark G-Sec", "Debt / cash", "Short gilt", "INF204KB18I3"),
    "LIQUIDBEES": ("Nippon India ETF Liquid BeES", "Debt / cash", "Liquid", "INF204KB17I5"),
}

# ---- pre-IPO, transcribed from the PE holding statement (account 9060965356)
# The statement's "Total Investment" is what was paid; there is no market price
# for an unlisted holding, so these sit at cost and are labelled as such.
PRE_IPO = [
    dict(name="Sterlite Grid 5", isin="INE03QT01027", units=18, price=0.00, cost=0.00,
         note="Allotted in a demerger; the statement carries no price for it, so it "
              "contributes nothing to the total rather than being guessed at."),
    dict(name="Sterlite Electric", isin="INE110V01015", units=18, price=575.50, cost=10359.00,
         note="Unlisted. Held at the statement price."),
    dict(name="Imagine Marketing (boAt)", isin="INE03AV01027", units=9, price=1236.00, cost=11124.00,
         note="Unlisted. Filed for an IPO; held at the statement price."),
]

# Noise words that identify a share class, not a fund. Stripping them leaves
# something a person recognises at a glance, which an ISIN never is.
_DROP = (
    "direct plan", "direct growth plan", "direct growth", "direct - growth",
    "- direct", "direct", "growth plan", "growth", "plan", "non demat",
    "non-demat", "regular", "(formerly", "fund of fund", "fund", "scheme",
)


def short_name(name: str) -> str:
    """A label for a board that is glanced at rather than read."""
    n = re.sub(r"\(.*?\)", " ", name)                  # drop parentheticals
    n = re.sub(r"\s+-\s+", " ", n)
    low = n.lower()
    for token in _DROP:
        low = low.replace(token, " ")
    keep, seen = [], set()
    for w in n.split():
        wl = re.sub(r"[^a-z0-9+]", "", w.lower())
        if not wl or wl in seen:
            continue
        if wl in {"direct", "growth", "plan", "fund", "scheme", "regular",
                  "of", "the", "nondemat", "demat", "erstwhile", "formerly"}:
            continue
        seen.add(wl)
        keep.append(w.strip("-,"))
        if len(keep) >= 4:
            break
    out = " ".join(keep).strip()
    return (out[:26].rstrip() or name[:26])


def mask_folio(folio: str) -> str:
    """A folio number identifies a mutual fund account, so only enough of it is
    kept to tell two folios of the same scheme apart. The US side's broker
    account number was removed for the same reason."""
    if folio.startswith("\u2026"):
        return folio                       # already masked; idempotent
    digits = "".join(ch for ch in folio if ch.isdigit())
    return f"\u2026{digits[-4:]}" if len(digits) > 4 else "\u2026"


def build():
    holdings = []

    # ---- mutual funds
    for r in json.loads((HERE / "data/sources/mf_cas_rows.json").read_text()):
        cls, sub = classify_fund(r["name"], r["isin"])
        holdings.append(dict(
            kind="mutual_fund", account="Mutual funds (CAS)",
            folio=mask_folio(r["folio"]),
            name=r["name"], symbol=short_name(r["name"]), isin=r["isin"],
            units=round(r["units"], 4), price=r["nav"], price_label="NAV",
            value=round(r["value"], 2), cost=round(r["cost"], 2),
            asset_class=cls, sub_class=sub, registrar=r["registrar"],
            priced_on=r["nav_date"], live=False))

    # ---- listed ETFs held at the broker
    with (HERE / "data/sources/zerodha_holdings.csv").open() as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("Instrument") or "").strip()
            if not sym:
                continue
            qty, avg, ltp = float(row["Qty"]), float(row["Price"]), float(row["LTP"])
            name, cls, sub, isin = ETF_META.get(
                sym, (sym, "India equity", "Other", ""))
            holdings.append(dict(
                kind="etf", account="Zerodha", folio=None,
                name=name, symbol=sym, isin=isin,
                # Yahoo carries NSE lines under a .NS suffix, which is how these
                # get a live price later
                quote_symbol=f"{sym}.NS",
                units=qty, price=ltp, price_label="LTP",
                value=round(qty * ltp, 2), cost=round(qty * avg, 2),
                asset_class=cls, sub_class=sub, priced_on=AS_OF, live=False))

    # ---- unlisted
    for p in PRE_IPO:
        holdings.append(dict(
            kind="pre_ipo", account="Pre-IPO (PE statement)", folio=None,
            name=p["name"], symbol=p["isin"], isin=p["isin"],
            units=p["units"], price=p["price"], price_label="Statement price",
            value=round(p["units"] * p["price"], 2), cost=round(p["cost"], 2),
            asset_class="Unlisted / pre-IPO", sub_class="Private",
            priced_on=AS_OF, live=False, unpriced=p["price"] == 0,
            note=p["note"]))

    by_account, by_class = {}, {}
    for h in holdings:
        h["pl"] = round(h["value"] - h["cost"], 2)
        h["pl_pct"] = round((h["value"] / h["cost"] - 1) * 100, 2) if h["cost"] else None
        for bucket, key in ((by_account, h["account"]), (by_class, h["asset_class"])):
            b = bucket.setdefault(key, {"value": 0.0, "cost": 0.0, "n": 0})
            b["value"] += h["value"]; b["cost"] += h["cost"]; b["n"] += 1
    for bucket in (by_account, by_class):
        for b in bucket.values():
            b["value"] = round(b["value"], 2); b["cost"] = round(b["cost"], 2)
            b["pl"] = round(b["value"] - b["cost"], 2)
            b["pl_pct"] = round((b["value"] / b["cost"] - 1) * 100, 2) if b["cost"] else None

    value = round(sum(h["value"] for h in holdings), 2)
    cost = round(sum(h["cost"] for h in holdings), 2)
    out = dict(
        as_of=AS_OF, currency="INR",
        totals=dict(value=value, cost=cost, pl=round(value - cost, 2),
                    pl_pct=round((value / cost - 1) * 100, 2),
                    holdings=len(holdings)),
        by_account=dict(sorted(by_account.items(), key=lambda kv: -kv[1]["value"])),
        by_class=dict(sorted(by_class.items(), key=lambda kv: -kv[1]["value"])),
        holdings=sorted(holdings, key=lambda h: -h["value"]))

    p = HERE / "data" / "india.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}  ({p.stat().st_size:,} bytes)")
    print(f"india: Rs {value:,.2f} on cost Rs {cost:,.2f}  "
          f"({out['totals']['pl_pct']:+.2f}%)  {len(holdings)} holdings")
    for k, b in out["by_class"].items():
        print(f"    {k:<22} {b['value']:>13,.0f}  ({b['value']/value*100:>5.1f}%)  {b['n']:>2} holdings")
    return out

if __name__ == "__main__":
    build()
