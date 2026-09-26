"""The news check (on unless NEWS_CHECK=off): before every buy or average, the shop looks for
serious bad news about the company and skips the buy if it finds some. Serious means fraud or
accounting problems, a regulator's ban, probe or penalty (SEBI, RBI, USFDA…), raids or arrests,
a default or insolvency, the auditor quitting, or a short-seller report.

Two layers, and either one can veto:
  1. Red-flag words (always on, free, no key needed): a headline that names the company and
     contains words like "fraud", "SEBI bans", "ED raids", "insolvency", "auditor resigns".
  2. Jev (with AI_GATEWAY_API_KEY): reads each headline that names the company and says whether
     it's serious bad news, catching what a word list misses ("licence cancelled", "profits
     collapse after write-off") and knowing when a scary word isn't bad ("SEBI lifts ban").

Serious news puts the stock on a watch-list for NEWS_COOLOFF_DAYS (10 by default): no buying or
averaging it, even after the headline has scrolled off the feeds. News about a whole group
("Adani Group") skips that day's buy for every company in the group, and goes on the watch-list
too if Jev confirms it. Headlines are collected every hour (the server's jev-news timer) into
results/headlines.json, so news from the morning or the night before isn't missed.
A skipped stock is treated as if it weren't in the Nifty 50 that day: the shop moves on to the next.
Nothing here sells: the check only stops new money going in. No filter is perfect, and the
backtest can't test it (there's no archive of old headlines).
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

from .core import RESULTS

# If a feed stops working, swap in another markets feed from the same site.
FEEDS = {
    "economic times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml",
    "livemint": "https://www.livemint.com/rss/markets",
    "business standard": "https://www.business-standard.com/rss/markets-106.rss",
}
ARCHIVE = RESULTS / "headlines.json"
FLAGS = RESULTS / "news_flags.json"
KEEP_DAYS = 7  # headlines kept in the archive
WEAK = {"the", "india", "indian", "asian", "state", "bharat", "power", "coal", "sun", "max", "hindustan"}

# Red-flag words. Each pattern is matched against the lower-cased headline and summary.
RED_FLAGS = {
    "fraud or accounting problems": r"fraud|scam|forensic audit|accounting (irregularit|lapse|fraud)|misappropriat|siphon|"
                                    r"embezzl|money[- ]laundering|round[- ]tripping|window[- ]dressing|whistle[- ]?blower",
    "a regulator's ban or probe": r"(sebi|rbi|cci|irdai|usfda|us fda|regulator|nclt|sfio|dgca)\W+(\w+\W+){0,3}"
                                  r"(bans?|barred|bars|debar|probe|probes|investigat|show[- ]cause|restrict|curbs?|"
                                  r"suspend|cancel|order against|action against)|debarred|import alert|warning letter",
    "raids or arrests": r"\braids?\b|\braided\b|searches at|\barrested\b|arrest of|arrests? (of )?(its )?(promoter|founder|"
                        r"director|ceo|md|chairman|cfo|executive|official)|enforcement directorate|"
                        r"\bed (probe|summons|attaches|searches)|\bcbi\b|income[- ]tax (raid|search)|\bi-t (raid|search)|\bfir\b",
    "default or insolvency": r"insolven|bankrupt|\bdefault(s|ed)?\b|nclt admits|pledge invo|invocation of pledge|"
                             r"downgrade(d)? to (junk|default|d\b)",
    "the auditor quitting": r"auditor (resign|quits|steps down|exits)|(resignation|exit) of (the )?(statutory )?auditor",
    "a short-seller report": r"short[- ]seller|hindenburg",
}
RED = {label: re.compile(p) for label, p in RED_FLAGS.items()}
CLEARED = re.compile(r"lifts? ban|revok\w* (the )?ban|clean chit|clears?\b|cleared|quash|acquit|dismiss\w* (the )?(case|plea|charges)|"
                     r"settles?\b|relief|no (fraud|wrongdoing)|denies|rejects? (the )?allegation")

QUESTION = ("Is this headline serious bad news for {company} (NSE: {symbol}) shares? Serious means things like fraud or "
            "accounting problems, a regulator's ban, probe or big penalty, raids or arrests of the company or its "
            "promoters, a default or insolvency, the auditor quitting, a short-seller report, or a business-threatening "
            "loss of a licence or major customer. Ordinary bad news (a weak quarter, a price target cut, a small fine) is "
            "only mildly negative.")


# ---------------------------------------------------------------- headlines

def fetch_headlines(hours: float, quiet: bool = False) -> list[dict]:
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
    items, seen = [], set()
    for source, url in FEEDS.items():
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (jev-shop rss reader)"})
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as exc:
            if not quiet:
                print(f"  ! feed {source} unavailable: {str(exc)[:80]}")
            continue
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip())
            pub = it.findtext("pubDate")
            if not title or not pub or title.lower() in seen:
                continue
            try:
                ts = pd.Timestamp(parsedate_to_datetime(pub))
                ts = (ts.tz_localize("Asia/Kolkata") if ts.tzinfo is None else ts).tz_convert("UTC")
            except (TypeError, ValueError):
                continue
            if ts < cutoff:
                continue
            summary = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))).strip()
            seen.add(title.lower())
            items.append({"source": source, "headline": title, "summary": summary[:400], "published": ts})
    return sorted(items, key=lambda x: x["published"])


def collect(quiet: bool = True) -> tuple[list[dict], int]:
    """Fetch the feeds, add anything new to the archive, and return the archive (newest last)
    plus how many headlines the feeds returned just now (0 = the feeds couldn't be read)."""
    fresh = fetch_headlines(48, quiet=quiet)
    try:
        old = json.loads(ARCHIVE.read_text())
    except (OSError, ValueError):
        old = []
    cutoff = time.time() - KEEP_DAYS * 86400
    merged = {x["headline"].lower(): x for x in old if x.get("t", 0) >= cutoff}
    for it in fresh:
        merged.setdefault(it["headline"].lower(), {"headline": it["headline"], "summary": it["summary"],
                                                   "source": it["source"], "t": it["published"].timestamp()})
    items = sorted(merged.values(), key=lambda x: x["t"])
    RESULTS.mkdir(exist_ok=True)
    tmp = ARCHIVE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items))
    os.replace(tmp, ARCHIVE)
    return items, len(fresh)


def matches(symbol: str, company: str, items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Headlines naming the company (by NSE symbol, full name or its first two words: "Tata Steel"), and
    headlines naming only its group (the first word of its name: "Tata"), each oldest first."""
    name = re.sub(r"\b(limited|ltd)\b\.?", "", company, flags=re.I).strip(" .").lower()
    words = name.split()
    strong = {symbol.lower(), name} | ({" ".join(words[:2])} if len(words) >= 2 else set())
    weak = {words[0]} if words and len(words[0]) >= 4 and words[0] not in WEAK else set()

    def hit(keys, it):
        text = _text(it)
        return any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text) for k in keys if len(k) >= 2)

    first = [it for it in items if hit(strong, it)]
    return first, [it for it in items if it not in first and hit(weak, it)]


def _text(it: dict) -> str:
    return (it["headline"] + " " + it.get("summary", "")).lower()


def red_flag(it: dict) -> str | None:
    text = _text(it)
    return next((label for label, pat in RED.items() if pat.search(text)), None)


def check_enabled() -> bool:
    return os.getenv("NEWS_CHECK", "on").strip().lower() not in ("off", "false", "0", "no")


def cooloff_days() -> int:
    try:
        return max(0, int(os.getenv("NEWS_COOLOFF_DAYS", "10")))
    except ValueError:
        return 10


# ---------------------------------------------------------------- the watch-list

class Flags:
    """Stocks with serious bad news, and until when they're off the shopping list."""

    def __init__(self):
        try:
            self.d = json.loads(FLAGS.read_text())
        except (OSError, ValueError):
            self.d = {}

    def save(self) -> None:
        RESULTS.mkdir(exist_ok=True)
        tmp = FLAGS.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, indent=1))
        os.replace(tmp, FLAGS)

    def active(self, symbol: str, today: date) -> dict | None:
        f = self.d.get(symbol)
        return f if f and f["until"] >= today.isoformat() else None

    def all_active(self, today: date) -> dict[str, dict]:
        return {s: f for s, f in self.d.items() if f["until"] >= today.isoformat()}

    def add(self, symbol: str, today: date, headline: str, why: str, by: str) -> bool:
        """Put a stock on the watch-list. Returns True if it wasn't already on it."""
        new = self.active(symbol, today) is None
        until = (today + timedelta(days=cooloff_days())).isoformat()
        self.d[symbol] = {"until": max(until, self.d.get(symbol, {}).get("until", "")), "headline": headline[:200],
                          "why": why, "by": by, "since": self.d.get(symbol, {}).get("since") if not new else today.isoformat()}
        for s in [s for s, f in self.d.items() if f["until"] < (today - timedelta(days=30)).isoformat()]:
            self.d.pop(s)  # forget flags a month after they end
        self.save()
        return new

    def clear(self, symbol: str) -> bool:
        found = self.d.pop(symbol, None) is not None
        self.save()
        return found


# ---------------------------------------------------------------- the check

def ask_jev(jev, symbol: str, company: str, it: dict) -> bool | None:
    """True = Jev says serious bad news, False = not, None = Jev couldn't answer."""
    q = {"impact": {"type": "choice", "instructions": QUESTION.format(company=company, symbol=symbol),
                    "criteria": {"serious_bad_news": None, "mildly_negative": None, "neutral_or_positive": None,
                                 "not_about_this_company": None}}}
    try:
        ans, _ = jev.ask({"headline": it["headline"], "summary": it.get("summary", ""), "source": it.get("source", "")},
                         q, timeout=8, retries=1)
    except Exception:
        return None
    a = ans["impact"]
    return a["choice"] == "serious_bad_news" and a["probs"].get("serious_bad_news", 0) >= 0.6


def screen(jev, symbol: str, company: str, items: list[dict], flags: Flags, today: date,
           deadline: float | None = None) -> str | None:
    """Why this stock mustn't be bought today, or None if the news looks fine."""
    f = flags.active(symbol, today)
    if f:
        return f"on the news watch-list until {f['until']} ({f['why']}: “{f['headline'][:80]}”)"
    own, group = matches(symbol, company, items)
    unclear = None
    for it in reversed(own):  # newest first
        label = red_flag(it)
        if not label:
            continue
        if CLEARED.search(_text(it)):
            unclear = unclear or (it, label)  # "SEBI lifts ban": let Jev judge it
            continue
        flags.add(symbol, today, it["headline"], label, "red-flag words")
        return f"serious bad news ({label}): “{it['headline'][:90]}”"
    group_hit = next(((it, red_flag(it)) for it in reversed(group) if red_flag(it) and not CLEARED.search(_text(it))), None)
    judged = set()  # headlines Jev read and found NOT serious
    if jev:
        for it in (list(reversed(own)) + list(reversed(group)))[:6]:
            if deadline and time.time() > deadline:
                break
            verdict = ask_jev(jev, symbol, company, it)
            if verdict:
                flags.add(symbol, today, it["headline"], "Jev: serious bad news", "Jev")
                return f"Jev read serious bad news: “{it['headline'][:90]}”"
            if verdict is False:
                judged.add(it["headline"])
    if unclear and unclear[0]["headline"] not in judged:  # a scary word that may be good news, unjudged: skip today only
        it, label = unclear
        return f"possible bad news ({label}), skipped today to be safe: “{it['headline'][:90]}”"
    if group_hit and group_hit[0]["headline"] not in judged:
        it, label = group_hit
        return f"bad news for its group ({label}), skipped today: “{it['headline'][:90]}”"
    return None


def watch(universe: dict[str, str], held: list[str], today: date) -> tuple[list[tuple[str, str]], int, Flags]:
    """The hourly job: collect headlines, and put any stock with red-flag news about it on the watch-list.
    Returns the newly flagged (symbol, headline), how many headlines the feeds returned, and the flags."""
    items, fresh = collect()
    flags = Flags()
    new = []
    recent = [it for it in items if it["t"] >= time.time() - 36 * 3600]
    for sym in sorted(set(universe) | set(held)):
        own, _ = matches(sym, universe.get(sym, sym), recent)
        for it in reversed(own):
            label = red_flag(it)
            if label and not CLEARED.search(_text(it)):
                if flags.add(sym, today, it["headline"], label, "red-flag words"):
                    new.append((sym, it["headline"]))
                break
    return new, fresh, flags
