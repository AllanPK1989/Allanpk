#!/usr/bin/env python3
"""
Build the consolidated dataset for the US portfolio dashboard.

Sources
-------
accounts   : the three broker statements, all dated 2026-09-05
market     : prices / 52-week ranges / multiples / consensus targets gathered
             from public sources on 2026-09-05 (see data/SOURCES.md)

Run:  python3 build_data.py     ->  data/portfolio.json
"""
import json, datetime, pathlib

AS_OF = "2026-09-05"
USDINR = 94.38

# ---------------------------------------------------------------- accounts
# (ticker, shares, avg_cost)  -- price comes from MARKET so every account
# is marked to the same tape.
ACCOUNTS = {
    "vested_1": {
        "label": "Vested · VSCH000079",
        "broker": "Vested / DriveWealth",
        "note": "Largest account. Statement PDF, 05 Sep 2026.",
        "holdings": [
            ("AAPL",  5.36527387, 192.29), ("AMZN", 10.9536297,  155.45),
            ("BITQ", 49.25419283,   9.54), ("BLOK", 13.1733312,   24.69),
            ("CIBR",  9.8733417,   52.75), ("CRWV",  4.87708596,  83.59),
            ("GOOGL",11.7348171,  145.09), ("IBIT", 16.31889774,  59.01),
            ("META",  3.3424877,  362.47), ("MSFT",  5.03863455, 397.43),
            ("NBIS",  5.25924698,  84.42), ("NVDA",  3.16406873, 161.18),
            ("SHOP", 17.06124511,  62.52), ("SMH",   6.26367852, 159.83),
            ("TSLA",  4.49570874, 193.05), ("TSM",   0.78155274, 295.95),
        ],
    },
    "vested_2": {
        "label": "Vested · Account 2",
        "broker": "Vested / DriveWealth",
        "note": "Second Vested account. Holdings table, 05 Sep 2026.",
        "holdings": [
            ("AAPL",  3.84240893, 211.91), ("AMZN",  9.7922358,  217.19),
            ("BLOK",  8.89881295,  43.37), ("CRWV",  3.62549155,  82.99),
            ("GOOGL", 5.11985079, 202.69), ("IREN", 10.58521408,  42.13),
            ("MELI",  0.22365349,1622.29), ("META",  3.4889153,  622.27),
            ("MSFT",  4.43266095, 403.37), ("MU",    3.76304958,  98.36),
            ("NBIS",  2.56411058,  96.25), ("NFLX",  6.30055407,  78.10),
            ("NVDA",  1.8873146,  220.74), ("RKLB",  7.99550024,  49.26),
            ("SHOP",  9.90084148, 108.73), ("SMH",   2.69764582, 216.86),
            ("VRT",   1.68850912, 178.02),
        ],
    },
    "ibkr": {
        "label": "IBKR · Open Positions",
        "broker": "Interactive Brokers",
        "note": "Smallest account, mostly recent entries. Statement, 05 Sep 2026.",
        "holdings": [
            ("AVGO", 2.1081, 380.306265357), ("BWXT", 1.0778, 186.012395621),
            ("CRWD", 0.4762, 190.555728685), ("IREN", 8.5665,  35.057899959),
            ("KLAC", 1.3808, 217.716926419), ("LRCX", 0.9365, 320.92390283),
            ("META", 0.8478, 636.856372965), ("MSFT", 1.7639, 397.258397868),
            ("MU",   0.6598, 910.583528342), ("NFLX", 7.2401,  69.080280521),
            ("NVDA", 2.8901, 207.852208228), ("RKLB", 4.4823,  67.091460634),
        ],
    },
}

# ---------------------------------------------------------------- market data
# px       : close 05 Sep 2026 (statements agree across accounts)
# lo/hi    : 52-week range
# fpe      : forward P/E   (None where not meaningfully defined / loss-making)
# tpe      : trailing P/E
# tgt      : consensus 12-month price target
# conf     : confidence in the fundamental figures  high | med | low
M = lambda **k: k
MARKET = {
 "AAPL": M(name="Apple", theme="Mega-cap", px=319.97, lo=223.78, hi=344.57, fpe=33.5, tpe=None, tgt=330.0, conf="high",
   note="Forward multiple has re-rated well ahead of a mid-single-digit earnings growth rate."),
 "AMZN": M(name="Amazon", theme="Mega-cap", px=258.51, lo=196.00, hi=287.20, fpe=22.0, tpe=35.3, tgt=327.67, conf="high",
   note="AWS growth accelerated to 24% on a $142B run-rate — fastest in 13 quarters."),
 "AVGO": M(name="Broadcom", theme="AI semis", px=357.895, lo=289.96, hi=495.00, fpe=None, tpe=45.6, tgt=509.41, conf="high",
   note="Q3 AI revenue $16.7B, +221% y/y, +54% q/q. Sold off ~3% on softer total-company guidance."),
 "BITQ": M(name="Bitwise Crypto Innovators ETF", theme="Crypto", px=26.62, lo=None, hi=None, fpe=None, tpe=None, tgt=None, conf="low",
   note="Crypto-equity basket. Moves with bitcoin beta, not with earnings."),
 "BLOK": M(name="Amplify Blockchain ETF", theme="Crypto", px=65.23, lo=None, hi=None, fpe=None, tpe=None, tgt=None, conf="low",
   note="Actively managed blockchain basket. Same bitcoin beta as BITQ — the two overlap heavily."),
 "BWXT": M(name="BWX Technologies", theme="Nuclear / defense", px=157.59, lo=105.07, hi=241.82, fpe=37.68, tpe=None, tgt=234.45, conf="high",
   note="Sole supplier of US naval nuclear reactors; SMR and medical isotopes as the option value."),
 "CIBR": M(name="First Trust Cybersecurity ETF", theme="Cyber", px=94.59, lo=60.07, hi=102.35, fpe=None, tpe=31.5, tgt=None, conf="med",
   note="Top holdings are PANW, FTNT, CRWD, CSCO, AVGO — so it duplicates the CRWD and AVGO positions."),
 "CRWD": M(name="CrowdStrike", theme="Cyber", px=213.10, lo=85.68, hi=233.88, fpe=None, tpe=None, tgt=226.57, conf="med",
   note="4-for-1 split on 2 Jul 2026. Premium SaaS multiple with the stock back near its high."),
 "CRWV": M(name="CoreWeave", theme="AI infra", px=89.36, lo=33.51, hi=187.00, fpe=None, tpe=None, tgt=144.46, conf="med",
   note="$51.6B debt against $5.5B cash; D/E 10.3. Enterprise value ~2x the equity market cap."),
 "GOOGL":M(name="Alphabet", theme="Mega-cap", px=338.46, lo=226.11, hi=408.61, fpe=17.0, tpe=16.8, tgt=415.00, conf="high",
   note="Cheapest mega-cap on forward earnings. Cloud and Gemini scaling; capex and antitrust are the overhang."),
 "IBIT": M(name="iShares Bitcoin Trust", theme="Crypto", px=45.23, lo=32.84, hi=71.82, fpe=None, tpe=None, tgt=None, conf="high",
   note="Spot bitcoin, ~$80k. The only losing position in the book. No earnings-based valuation applies."),
 "IREN": M(name="IREN Ltd", theme="AI infra", px=44.68, lo=25.31, hi=76.87, fpe=None, tpe=None, tgt=79.34, conf="med",
   note="$3.4B five-year NVIDIA AI-cloud contract; targeting $3.7B ARR by end-2026. Ex-bitcoin miner."),
 "KLAC": M(name="KLA Corp", theme="Semi equipment", px=185.60, lo=87.20, hi=306.70, fpe=42.34, tpe=57.6, tgt=231.78, conf="med",
   note="10-for-1 split. Process control is the highest-margin niche in WFE, but the multiple is full."),
 "LRCX": M(name="Lam Research", theme="Semi equipment", px=307.65, lo=100.68, hi=438.50, fpe=32.66, tpe=None, tgt=370.87, conf="high",
   note="Levered to memory capex — the same cycle that drives MU, so the two are one bet, not two."),
 "MELI": M(name="MercadoLibre", theme="Intl e-commerce", px=1978.37, lo=1495.00, hi=2548.50, fpe=40.0, tpe=49.7, tgt=2264.88, conf="med",
   note="LatAm commerce + fintech compounder. Smallest position in the book relative to its quality."),
 "META": M(name="Meta Platforms", theme="Mega-cap", px=616.77, lo=520.26, hi=790.80, fpe=15.0, tpe=None, tgt=754.77, conf="high",
   note="~15x forward — cheapest mega-cap. Capex guided to $130–145B; Q2 FCF collapsed to $784M from $8.6B."),
 "MSFT": M(name="Microsoft", theme="Mega-cap", px=499.70, lo=349.20, hi=553.72, fpe=25.41, tpe=None, tgt=571.38, conf="high",
   note="Azure +43%, past $100B annual revenue; contracted backlog $678B. Supply, not demand, is the constraint."),
 "MU":   M(name="Micron", theme="Memory", px=1016.59, lo=128.40, hi=1255.00, fpe=12.5, tpe=21.5, tgt=1513.11, conf="high",
   note="Up ~7x in 52 weeks. HBM sold out for 2026, gross margin ~57%. The low P/E is peak-cycle EPS in the denominator."),
 "NBIS": M(name="Nebius Group", theme="AI infra", px=226.39, lo=63.26, hi=299.86, fpe=None, tpe=None, tgt=286.69, conf="med",
   note="AI neocloud, still pre-profit. Up 168% on cost in this book."),
 "NFLX": M(name="Netflix", theme="Consumer tech", px=78.25, lo=65.08, hi=126.71, fpe=20.0, tpe=None, tgt=93.00, conf="high",
   note="10-for-1 split Nov 2025. Down 38% from the high and ~20x forward against a 30–45x history."),
 "NVDA": M(name="NVIDIA", theme="AI semis", px=230.36, lo=164.07, hi=236.54, fpe=18.61, tpe=28.4, tgt=325.99, conf="high",
   note="18.6x forward is the cheapest this franchise has looked in years — but it sits 3% off its high."),
 "RKLB": M(name="Rocket Lab", theme="Space", px=64.26, lo=37.57, hi=151.00, fpe=None, tpe=None, tgt=111.00, conf="med",
   note="Neutron on track for Q4 2026 pad delivery at $50–55M pricing. Still loss-making."),
 "SHOP": M(name="Shopify", theme="Software", px=145.09, lo=94.00, hi=182.19, fpe=None, tpe=None, tgt=167.02, conf="med",
   note="Up 132% on cost in the largest account. Fairly priced against its growth now."),
 "SMH":  M(name="VanEck Semiconductor ETF", theme="Semi ETF", px=567.01, lo=289.25, hi=671.83, fpe=None, tpe=38.73, tgt=None, conf="high",
   note="25 largest US-listed semis. The efficient way to hold semi beta while trimming single names."),
 "TSLA": M(name="Tesla", theme="Consumer tech", px=354.08, lo=297.38, hi=498.83, fpe=192.0, tpe=324.8, tgt=390.09, conf="high",
   note="192x forward. The valuation rests on robotaxi and Optimus, neither of which is a revenue line yet."),
 "TSM":  M(name="TSMC", theme="AI semis", px=428.92, lo=241.62, hi=479.00, fpe=27.09, tpe=None, tgt=552.38, conf="high",
   note="Effective monopoly on leading-edge logic at a discount to the semi median. Taiwan risk is the discount."),
 "VRT":  M(name="Vertiv Holdings", theme="AI infra", px=280.53, lo=118.70, hi=379.94, fpe=42.0, tpe=60.8, tgt=337.50, conf="high",
   note="Power and thermal management for data centres — the pick-and-shovel on the AI build-out."),
 # ---- watchlist-only names the user asked to add ----
 "ASML": M(name="ASML Holding", theme="Semi equipment", px=1677.97, lo=611.80, hi=1741.00, fpe=39.84, tpe=None, tgt=1882.22, conf="high",
   note="EUV monopoly, but 39.8x forward is 31% above the semi median and the stock is 4% off its high."),
 "AMD":  M(name="Advanced Micro Devices", theme="AI semis", px=477.57, lo=149.22, hi=584.73, fpe=None, tpe=None, tgt=610.00, conf="low",
   note="Data-centre revenue +107% y/y; MI400 ramping. Forward EPS estimates are dispersed enough that a forward P/E is not trustworthy."),
 "INTC": M(name="Intel", theme="Semi turnaround", px=95.80, lo=23.75, hi=142.34, fpe=None, tpe=None, tgt=112.44, conf="med",
   note="Up 268% in a year on the 18A ramp and NVIDIA's equity investment. Consensus rating is Hold, not Buy."),
 "PLTR": M(name="Palantir", theme="Software", px=182.53, lo=None, hi=None, fpe=115.05, tpe=92.7, tgt=198.00, conf="high",
   note="Revenue +79% and a 42.8% operating margin — but 115x forward is 484% above the software median."),
 "PANW": M(name="Palo Alto Networks", theme="Cyber", px=331.94, lo=139.57, hi=398.88, fpe=87.69, tpe=351.8, tgt=390.50, conf="high",
   note="Revenue +24.5% to $11.48B. At 87.7x forward the multiple is 340% above the software median."),
 "NOW":  M(name="ServiceNow", theme="Software", px=145.59, lo=81.24, hi=194.73, fpe=30.55, tpe=86.5, tgt=173.31, conf="high",
   note="5-for-1 split Dec 2025. Down 22.7% over a year on no fundamental break — 30.6x forward against a 50–60x history."),
}

# ---------------------------------------------------------------- scoring
SECTOR_MEDIAN_FPE = {
    "AI semis": 30.4, "Semi equipment": 30.4, "Memory": 30.4, "Semi turnaround": 30.4,
    "Semi ETF": 30.4, "Software": 19.9, "Cyber": 19.9, "Mega-cap": 22.0,
    "Consumer tech": 22.0, "AI infra": 30.0, "Intl e-commerce": 22.0,
    "Space": 30.0, "Nuclear / defense": 25.0, "Crypto": None,
}

def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def score(t, m):
    """Return (valuation 0-100, entry 0-100, components dict).

    valuation : how much cheaper than fair the name looks
    entry     : how good today's price is as an entry point
    Higher is better on both. Components are exposed so the page can show the math.
    """
    px, lo, hi, fpe, tgt = m["px"], m["lo"], m["hi"], m["fpe"], m["tgt"]
    comp = {}

    # --- valuation leg 1: upside to consensus target (0-100, 40% weight)
    if tgt:
        up = (tgt / px - 1) * 100
        comp["upside_pct"] = round(up, 1)
        s_up = clamp(50 + up * 1.6)          # 0% upside -> 50, +30% -> 98
    else:
        up, s_up = None, 50.0
        comp["upside_pct"] = None

    # --- valuation leg 2: forward P/E vs sector median (40%)
    med = SECTOR_MEDIAN_FPE.get(m["theme"])
    if fpe and med:
        prem = (fpe / med - 1) * 100          # negative = cheaper than sector
        comp["fpe_prem_pct"] = round(prem, 1)
        s_pe = clamp(50 - prem * 0.9)         # -40% premium -> 86, +80% -> 0
    else:
        prem, s_pe = None, 50.0
        comp["fpe_prem_pct"] = None

    # --- valuation leg 3: position in the 52-week range (20%)
    if lo and hi and hi > lo:
        rng = (px - lo) / (hi - lo) * 100
        comp["range_pct"] = round(rng, 1)
        comp["off_high_pct"] = round((1 - px / hi) * 100, 1)
        s_rng = clamp(100 - rng)               # lower in the range scores better
    else:
        rng, s_rng = None, 50.0
        comp["range_pct"] = comp["off_high_pct"] = None

    valuation = round(0.40 * s_up + 0.40 * s_pe + 0.20 * s_rng, 1)

    # --- entry quality: reward a real pullback, penalise both extremes
    # Best entries sit 12-35% off the high: deep enough to matter, not a broken chart.
    if comp["off_high_pct"] is not None:
        oh = comp["off_high_pct"]
        if oh < 5:      s_entry = 25          # extended, no margin of safety
        elif oh < 12:   s_entry = 45 + (oh - 5) * 4.3
        elif oh <= 35:  s_entry = 75 + (oh - 12) * 1.1     # the sweet spot
        elif oh <= 50:  s_entry = 100 - (oh - 35) * 2.7    # getting broken
        else:           s_entry = 55 - (oh - 50) * 1.2     # falling knife
        entry = round(clamp(s_entry), 1)
    else:
        entry = 50.0
    return valuation, entry, comp

# hand-set verdicts: the score ranks, judgement decides. Both are shown.
VERDICT = {
 "AVGO":("STRONG BUY","Quality franchise marked down 28% on a guidance quibble while AI revenue tripled."),
 "GOOGL":("STRONG BUY","Cheapest mega-cap on forward earnings, 17% off the high, ~23% to consensus."),
 "NOW":("BUY","Best-in-class enterprise software de-rated to 30x forward from a 50-60x history."),
 "NFLX":("BUY","38% off the high, near the 52-week low, ~20x forward against a 30-45x history."),
 "META":("BUY","~15x forward is the cheapest mega-cap multiple — the capex question is why."),
 "BWXT":("BUY","35% off the high with a monopoly backlog and ~49% to consensus."),
 "MELI":("BUY","22% off the high; the smallest position in the book relative to its quality."),
 "VRT":("BUY","26% off the high; direct pick-and-shovel on data-centre power and cooling."),
 "TSM":("BUY","27x forward for the leading-edge monopoly, ~29% to consensus."),
 "AMZN":("ACCUMULATE","AWS re-accelerating at 22x forward; add on weakness rather than here."),
 "NVDA":("BUY THE DIP","18.6x forward is genuinely cheap, but it sits 3% off the high. Wait for <$210."),
 "IREN":("SPECULATIVE BUY","Highest consensus upside in the book — and an ex-miner balance sheet. Size small."),
 "MSFT":("HOLD","Fairly valued at 25.4x for 43% Azure growth. Add below ~$460."),
 "LRCX":("HOLD","30% off the high, but it is the same memory-capex bet as MU."),
 "KLAC":("HOLD","Down 39% from the high yet still 42x forward. Wait."),
 "SHOP":("HOLD","Fairly valued after a 132% run. Nothing to add here."),
 "NBIS":("HOLD","Up 168%; still pre-profit. Let it run, don't add."),
 "SMH":("HOLD","The cleanest way to hold semi beta while single names get trimmed."),
 "CIBR":("HOLD","Duplicates the CRWD and AVGO exposure already held directly."),
 "RKLB":("SPECULATIVE HOLD","Down 57%; Neutron is the whole thesis and it has not flown."),
 "IBIT":("HOLD","A bitcoin proxy. Rebalance to a target weight — never average down mechanically."),
 "CRWV":("DO NOT ADD","$51.6B of debt against $5.5B of cash. The leverage, not the demand, is the risk."),
 "CRWD":("DO NOT ADD","Back near the high with ~6% to consensus. Fails the valuation screen."),
 "BITQ":("TRIM","+179% on cost, and it overlaps BLOK almost entirely."),
 "BLOK":("TRIM","+164% on cost, and it overlaps BITQ almost entirely."),
 "AAPL":("TRIM","33.5x forward for mid-single-digit growth, 7% off the high, ~3% to consensus."),
 "TSLA":("TRIM","192x forward. Book part of the 83% gain."),
 "MU":("TRIM / TAKE PROFITS","Up ~7x in 52 weeks. A 12.5x P/E on peak-cycle EPS is the classic memory trap."),
 "ASML":("WATCH","Fine business, wrong price: 39.8x forward and 4% off the high. Revisit under ~$1,450."),
 "AMD":("WATCH","Story is real, but forward estimates are too dispersed to underwrite a multiple."),
 "INTC":("AVOID","Already +268% in a year and the consensus rating is Hold. The turnaround is priced."),
 "PLTR":("AVOID","115x forward — 484% above the software median. Great company, no margin of safety."),
 "PANW":("AVOID","87.7x forward for 24% growth. Own the growth through CIBR instead."),
}

# ---------------------------------------------------------------- assemble
positions, per_account = {}, {}
for aid, acc in ACCOUNTS.items():
    rows, tot_v, tot_c = [], 0.0, 0.0
    for tkr, sh, cost in acc["holdings"]:
        px = MARKET[tkr]["px"]
        val, basis = sh * px, sh * cost
        rows.append(dict(ticker=tkr, shares=round(sh, 8), avg_cost=round(cost, 4),
                         price=px, value=round(val, 2), cost_basis=round(basis, 2),
                         pl=round(val - basis, 2),
                         pl_pct=round((val / basis - 1) * 100, 2) if basis else None))
        tot_v += val; tot_c += basis
        p = positions.setdefault(tkr, dict(shares=0.0, basis=0.0, accounts={}))
        p["shares"] += sh; p["basis"] += basis; p["accounts"][aid] = round(val, 2)
    rows.sort(key=lambda r: -r["value"])
    per_account[aid] = dict(**{k: v for k, v in acc.items() if k != "holdings"},
                            id=aid, holdings=rows,
                            value=round(tot_v, 2), cost=round(tot_c, 2),
                            pl=round(tot_v - tot_c, 2),
                            pl_pct=round((tot_v / tot_c - 1) * 100, 2))

total_value = sum(a["value"] for a in per_account.values())
total_cost  = sum(a["cost"]  for a in per_account.values())

universe = []
for tkr, m in MARKET.items():
    held = tkr in positions
    v, e, comp = score(tkr, m)
    verdict, why = VERDICT[tkr]
    rec = dict(ticker=tkr, held=held, **{k: m[k] for k in
               ("name","theme","px","lo","hi","fpe","tpe","tgt","conf","note")},
               val_score=v, entry_score=e, combined=round(0.6*v + 0.4*e, 1),
               verdict=verdict, why=why, **comp)
    if held:
        p = positions[tkr]
        val = p["shares"] * m["px"]
        rec.update(shares=round(p["shares"], 6), cost_basis=round(p["basis"], 2),
                   value=round(val, 2), pl=round(val - p["basis"], 2),
                   pl_pct=round((val / p["basis"] - 1) * 100, 2),
                   weight=round(val / total_value * 100, 2),
                   avg_cost=round(p["basis"] / p["shares"], 2),
                   accounts=p["accounts"])
    universe.append(rec)
universe.sort(key=lambda r: (-(r.get("value") or 0), r["ticker"]))

themes = {}
for r in universe:
    if r["held"]:
        themes[r["theme"]] = round(themes.get(r["theme"], 0) + r["value"], 2)

out = dict(
    as_of=AS_OF, generated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    usdinr=USDINR,
    totals=dict(value=round(total_value, 2), cost=round(total_cost, 2),
                pl=round(total_value - total_cost, 2),
                pl_pct=round((total_value / total_cost - 1) * 100, 2),
                value_inr=round(total_value * USDINR, 0), positions=len(positions),
                tickers_tracked=len(MARKET)),
    accounts=[per_account[k] for k in ("vested_1", "vested_2", "ibkr")],
    universe=universe,
    themes=dict(sorted(themes.items(), key=lambda kv: -kv[1])),
)

p = pathlib.Path(__file__).parent / "data" / "portfolio.json"
p.write_text(json.dumps(out, indent=1))
print(f"wrote {p}  ({p.stat().st_size:,} bytes)")
print(f"consolidated: ${total_value:,.2f} / cost ${total_cost:,.2f} / "
      f"P&L ${total_value-total_cost:,.2f} ({(total_value/total_cost-1)*100:.2f}%)")
print(f"{len(positions)} held positions, {len(MARKET)} tickers tracked")

# ---------------------------------------------------------------- dashboard
tpl = pathlib.Path(__file__).parent / "dashboard.template.html"
if tpl.exists():
    html = tpl.read_text().replace("__DATA__", json.dumps(out, separators=(",", ":")))
    dash = pathlib.Path(__file__).parent / "dashboard.html"
    dash.write_text(html)
    print(f"wrote {dash}  ({dash.stat().st_size:,} bytes)")
