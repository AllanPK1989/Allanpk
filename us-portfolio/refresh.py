#!/usr/bin/env python3
"""
Refresh prices and 52-week ranges from your own machine, then rebuild the
dashboard. Run this before the open, or whenever you want the book marked.

    python3 refresh.py            # fetch, rewrite MARKET prices, rebuild
    python3 refresh.py --dry-run  # show what would change, write nothing

No API key and no dependencies beyond the standard library. If a ticker fails
it keeps the previous value and says so — it never silently invents a price.
"""
import argparse, datetime, json, re, pathlib, sys, urllib.request, urllib.error

HERE = pathlib.Path(__file__).parent

# NYSE full-day closures for 2026. Advisory only: a date missing from this list
# just costs one wasted fetch, it never blocks a refresh you asked for.
HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
}


def last_session(today=None):
    """Most recent date US equities actually traded, on or before today."""
    d = today or datetime.date.today()
    for _ in range(10):
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS_2026:
            return d
        d -= datetime.timedelta(days=1)
    return d


def next_session(today=None):
    d = (today or datetime.date.today()) + datetime.timedelta(days=1)
    for _ in range(10):
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS_2026:
            return d
        d += datetime.timedelta(days=1)
    return d
SRC = HERE / "build_data.py"
UA = {"User-Agent": "Mozilla/5.0 (portfolio-dashboard refresh)"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=1y&interval=1d"


def quote(ticker):
    """Return (price, low52, high52) or raise."""
    req = urllib.request.Request(CHART.format(ticker), headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        meta = json.load(r)["chart"]["result"][0]["meta"]
    px = meta.get("regularMarketPrice")
    if not px:
        raise ValueError("no price in response")
    return px, meta.get("fiftyTwoWeekLow"), meta.get("fiftyTwoWeekHigh")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="fetch even when the file already holds the latest close")
    args = ap.parse_args()

    src = SRC.read_text()

    # Don't fire 33 requests at a closed market for prices we already hold.
    held = re.search(r'AS_OF = "([\d-]+)"', src)
    last = last_session()
    today = datetime.date.today()
    if held and not args.force:
        have = held.group(1)
        if have >= last.isoformat():
            print(f"Already current. The last US session closed "
                  f"{last:%a %d %b %Y}; this file holds {have}.")
            if today != last:
                print(f"Markets are shut today ({today:%a %d %b}); "
                      f"they reopen {next_session():%a %d %b %Y}.")
            print("Nothing to fetch. Use --force to refresh anyway.")
            return 0
    # entries are column-aligned, so the colon may be followed by padding
    tickers = re.findall(r'^ "([A-Z]+)":\s*M\(', src, re.M)
    print(f"refreshing {len(tickers)} tickers\n")

    updates, failed = {}, []
    for t in tickers:
        try:
            px, lo, hi = quote(t)
            updates[t] = (px, lo, hi)
            print(f"  {t:<6} {px:>10,.2f}")
        except Exception as e:                       # noqa: BLE001 - report, continue
            failed.append(t)
            print(f"  {t:<6} {'FAILED':>10}  ({type(e).__name__}: {e})")

    if failed:
        print(f"\n{len(failed)} failed, keeping their previous values: {', '.join(failed)}")
    if not updates:
        print("\nNothing fetched. Check your network, then retry.")
        return 1

    def entry_span(text, ticker):
        """Exact bounds of one M(...) call, by matching its parentheses."""
        m = re.search(r'^ "%s":\s*M\(' % ticker, text, re.M)
        if not m:
            return None
        i, depth = m.end() - 1, 0
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    return m.end(), i
            i += 1
        return None

    new, changed = src, 0
    for t, (px, lo, hi) in updates.items():
        span = entry_span(new, t)
        if not span:
            print(f"  ! {t}: entry not found in {SRC.name}, skipped")
            continue
        a, b = span
        body = new[a:b]
        body = re.sub(r"px=[\d.]+", f"px={px:.2f}", body)
        if lo:
            body = re.sub(r"lo=(?:[\d.]+|None)", f"lo={lo:.2f}", body)
        if hi:
            body = re.sub(r"hi=(?:[\d.]+|None)", f"hi={hi:.2f}", body)
        new = new[:a] + body + new[b:]
        changed += 1
    print(f"\nrewrote {changed} entries")

    if args.dry_run:
        print("\n--dry-run: build_data.py not modified.")
        return 0

    SRC.write_text(new)
    print(f"\nupdated {SRC.name}; rebuilding…\n")
    import subprocess
    return subprocess.call([sys.executable, str(HERE / "build_data.py")])


if __name__ == "__main__":
    raise SystemExit(main())
