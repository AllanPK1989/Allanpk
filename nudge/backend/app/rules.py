"""Built-in rules that turn a short note into tasks or commands, with no AI.

Used in demo mode and whenever Claude can't be reached, so voice capture never dead-ends.
It handles everyday phrasing: several tasks in one breath, dates ("tomorrow 5pm", "next Tuesday",
"by Friday", "25/11", "end of the month"), repeats ("every Monday", "first Monday of every month"),
priority words, people ("follow up with Ravi"), baskets by keyword, and commands
("mark the vendor call done", "move PM report to Monday", "what's pending with Ravi?").
Claude does all of this better; these rules keep the app useful without it.
"""
import calendar
import re
from dataclasses import dataclass, field
from datetime import date, time, timedelta

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}
DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
    "sep": 9, "sept": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "couple of": 2, "few": 3}
ORDINAL_WORDS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4,
                 "4th": 4, "last": -1}

WD = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues|tue|wed|thurs|thur|thu|fri|sat|sun)"
MON = (r"(january|february|march|april|may|june|july|august|september|october|november|december|"
       r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)")
PREP = r"(?:\b(?:on|by|before|for|due|till|until|at|from)\s+)?"

ACTION_VERBS = set("""
call phone ring send email e-mail mail pay book buy order follow followup remind check review prepare
submit meet schedule finish complete update ask get collect fix plan write read study renew visit
arrange share confirm discuss talk message text whatsapp ping raise approve close clear file sign
print test inspect chase organise organize register apply attend pick drop clean transfer deposit
draft reply respond return bring take make create set give tell speak sort look find contact
cancel start upload download install repair replace calibrate service lubricate audit train teach
revise practice practise watch learn note record log invite thank wish greet visit go do pass
""".split())
FILLERS = [
    r"okay so", r"ok so", r"so", r"hey nudge", r"nudge", r"um+", r"uh+", r"please", r"also", r"and",
    r"then", r"plus", r"next", r"add( a)?( task)?( to)?", r"create( a)?( task)?( to)?", r"new task",
    r"make a note to", r"note to self", r"remind me to", r"remember to", r"don'?t forget to",
    r"i need to", r"i have to", r"i've got to", r"i got to", r"i must", r"i should", r"i want to",
    r"i'd like to", r"need to", r"have to", r"got to", r"gotta", r"must", r"let'?s", r"we need to",
    r"i will", r"i'll", r"to",
]
FILLER_RE = re.compile(r"^(?:(?:" + "|".join(FILLERS) + r")\b[\s,]*)+", re.I)
ROLE_WORDS = {"vendor", "supplier", "team", "boss", "manager", "hr", "accounts", "purchase", "stores",
              "contractor", "client", "customer", "plumber", "electrician", "landlord", "bank", "doctor",
              "auditor", "supervisor", "sir", "madam"}
NOT_NAMES = set(WEEKDAYS) | set(MONTHS) | {
    "i", "me", "him", "her", "them", "us", "the", "a", "an", "my", "our", "this", "that", "it", "today",
    "tomorrow", "tonight", "everyone", "all", "someone", "pm", "am", "report", "and", "about", "regarding",
    "on", "to", "for", "at", "by", "next", "week", "month", "morning", "evening", "afternoon", "urgent",
    "asap", "important", "follow", "up", "email", "call", "meeting", "office", "home", "work", "time",
    "end", "day", "plant", "line", "machine", "quote", "quotation", "invoice", "payment", "regards",
}
PERSON_TRIGGERS = (
    r"follow(?:\s|-)?up\s+with|follow(?:\s|-)?up\s+on\s+\w+\s+with|chase(?:\s+up)?|remind|call|phone|ring|"
    r"e-?mail|mail|message|text|whatsapp|ping|ask|tell|meet(?:ing)?(?:\s+with)?|talk\s+to|speak\s+(?:to|with)|"
    r"check\s+with|confirm\s+with|discuss\s+with|catch\s+up\s+with|sync\s+with|with|from|"
    r"waiting\s+(?:for|on)|(?:send|submit|give|hand\s+over|forward)\s+(?:\w+\s+){0,4}?to|"
    r"share\s+(?:\w+\s+){0,3}?with|pay|thank|visit"
)
WAITING_RE = re.compile(
    r"\b(follow(?:\s|-)?up|chase|waiting\s+(?:for|on)|pending\s+from|expect(?:ing)?|awaiting|"
    r"remind\s+(?!me\b)\w+(?:\s+\w+)?\s+(?:to|about|on|of)|get\s+back|to\s+(?:send|share|reply|revert|confirm|"
    r"submit|give|provide|deliver|return|approve))\b",
    re.I,
)
PRIORITY_HIGH = re.compile(r"\b(urgent(?:ly)?|asap|as soon as possible|important|high priority|top priority|"
                           r"critical|priority one|p1|immediately)\b", re.I)
PRIORITY_LOW = re.compile(r"\b(low priority|whenever|someday|some day|no rush|not urgent|if time permits|"
                          r"when (?:i|you) get (?:a )?(?:chance|time))\b", re.I)

CATEGORIES = {
    "finance": r"pay|paid|bill|bills|emi|invoice|tax|gst|tds|insurance|premium|bank|loan|rent|salary|payment|"
               r"transfer|deposit|credit card|mutual fund|sip|investment|electricity bill|broadband|recharge|"
               r"fees|fee|reimbursement|expense|expenses|claim|itr|pan card",
    "learning": r"study|cmrp|course|exam|learn|chapter|revise|revision|practice test|mock test|lesson|class|"
                r"certification|training|tutorial|webinar|lecture|syllabus",
    "meetings": r"meeting|minutes|mom|action point|action points|agenda|standup|stand-up|review meeting|"
                r"presentation|townhall|town hall",
    "home": r"home|house|family|kids|son|daughter|wife|husband|mom|mother|dad|father|amma|appa|parents|"
            r"grocery|groceries|school|vegetables|gas cylinder|birthday|anniversary|maid|milk|"
            r"plumber|carpenter|painting|car service|bike service",
    "personal": r"gym|haircut|dentist|passport|licence|license|personal|health|walk|yoga|shopping|"
                r"aadhaar|aadhar|checkup|check-up|medicine|doctor|eye test|run|jog",
    "projects": r"project|milestone|proposal|rollout|roll out|implementation|phase \d|design review|"
                r"launch|kaizen|capex|pilot|poc|business case",
}
CATEGORY_RES = {k: re.compile(r"\b(?:" + v + r")\b", re.I) for k, v in CATEGORIES.items()}
CATEGORY_NAME_HINTS = {
    "work": ("work", "office", "job"), "projects": ("project",), "meetings": ("meeting", "action"),
    "personal": ("personal", "self"), "home": ("home", "family", "house"),
    "finance": ("finance", "bill", "money"), "learning": ("learn", "study", "course"),
}


@dataclass
class Draft:
    title: str
    notes: str = ""
    basket_id: int | None = None
    due_date: date | None = None
    due_time: time | None = None
    priority: str = "normal"
    person: str = ""
    waiting: bool = False
    repeat_rule: str = ""
    checklist: list[str] = field(default_factory=list)
    guessed: list[str] = field(default_factory=list)


@dataclass
class Interpretation:
    intent: str  # create | complete | reschedule | query | unclear
    drafts: list[Draft] = field(default_factory=list)
    targets: list[dict] = field(default_factory=list)  # {task_id, due_date, due_time}
    answer: str = ""
    match_ids: list[int] = field(default_factory=list)


# ---- dates and times -------------------------------------------------------------------------

def _num(word: str) -> int | None:
    word = word.lower().strip()
    if word.isdigit():
        return int(word)
    return NUMBER_WORDS.get(word)


def _hour(h: int, m: int, mer: str | None) -> time | None:
    mer = (mer or "").lower().replace(".", "")
    if mer.startswith("p") and h < 12:
        h += 12
    elif mer.startswith("a") and h == 12:
        h = 0
    elif not mer and 1 <= h <= 7:
        h += 12  # "at 5" during the day means 5 pm
    if 0 <= h <= 23 and 0 <= m <= 59:
        return time(h, m)
    return None


def _next_weekday(today: date, wd: int, include_today: bool = False) -> date:
    days = (wd - today.weekday()) % 7
    if days == 0 and not include_today:
        days = 7
    return today + timedelta(days=days)


def _cut(text: str, m: re.Match) -> str:
    return (text[: m.start()] + " " + text[m.end():]).strip()


def _safe_date(y: int, mth: int, d: int) -> date | None:
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def extract_time(text: str) -> tuple[time | None, str]:
    patterns = [
        (re.compile(r"\b(?:at|by|around|before|@)\s*(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?)?", re.I),
         lambda m: _hour(int(m[1]), int(m[2]), m[3])),
        (re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?=\W|$)", re.I),
         lambda m: _hour(int(m[1]), int(m[2] or 0), m[3])),
        (re.compile(r"\b(?:at|by|around|before)\s+(\d{1,2})(?:\s*o'?\s?clock)?\b(?!\s*(?:days?|weeks?|months?|"
                    r"st|nd|rd|th|/|-|\.\d))", re.I),
         lambda m: _hour(int(m[1]), 0, None)),
        (re.compile(r"\b(\d{1,2})\s*o'?\s?clock\b", re.I), lambda m: _hour(int(m[1]), 0, None)),
        (re.compile(r"\b(?:at\s+|by\s+)?(noon|midday|lunch ?time)\b", re.I), lambda m: time(12, 0)),
        (re.compile(r"\b(?:in the |this )?morning\b", re.I), lambda m: time(9, 0)),
        (re.compile(r"\b(?:in the |this )?afternoon\b", re.I), lambda m: time(15, 0)),
        (re.compile(r"\b(?:in the |this )?evening\b", re.I), lambda m: time(18, 0)),
        (re.compile(r"\btonight\b", re.I), lambda m: time(20, 0)),
    ]
    for rx, fn in patterns:
        m = rx.search(text)
        if m:
            t = fn(m)
            if t:
                keep_word = m[0].lower().strip() == "tonight"
                return t, text if keep_word else _cut(text, m)
    return None, text


def extract_date(text: str, today: date) -> tuple[date | None, str, bool]:
    """Returns (date, text without the date words, vague) — vague means we guessed a day."""
    rules: list[tuple[str, object]] = [
        (r"\bday after tomorrow\b", lambda m: (today + timedelta(days=2), False)),
        (r"\b(?:tomorrow|tmrw|tmr|tomo)\b", lambda m: (today + timedelta(days=1), False)),
        (r"\b(?:today|tonight|this evening|this afternoon|this morning|eod|end of (?:the )?day)\b",
         lambda m: (today, False)),
        (r"\bin\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|a couple of|a few)\s+"
         r"(day|days|week|weeks|month|months)\b",
         lambda m: (_in_n(today, m[1], m[2]), False)),
        (r"\b(?:by |before )?(?:the )?end of (?:the |this )?week\b|\beow\b",
         lambda m: (_end_of_week(today), False)),
        (r"\b(?:by |before )?(?:the )?(?:end of (?:the |this )?month|month[- ]end)\b",
         lambda m: (date(today.year, today.month, calendar.monthrange(today.year, today.month)[1]), False)),
        (r"\bnext month\b", lambda m: (_add_months(today.replace(day=1), 1), True)),
        (r"\b(?:this |the )?weekend\b", lambda m: (_next_weekday(today, 5, include_today=True), True)),
        (r"\bnext week\b", lambda m: (_next_weekday(today, 0), True)),
        (r"\bnext\s+" + WD + r"\b", lambda m: (_next_week_day(today, WEEKDAYS[m[1].lower()]), False)),
        (r"\bthis\s+(?:coming\s+)?" + WD + r"\b",
         lambda m: (_next_weekday(today, WEEKDAYS[m[1].lower()], include_today=True), False)),
        (r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + MON + r"\b(?:,?\s+(\d{4}))?",
         lambda m: (_dm(today, int(m[1]), MONTHS[m[2].lower()], m[3]), False)),
        (r"\b" + MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4}))?",
         lambda m: (_dm(today, int(m[2]), MONTHS[m[1].lower()], m[3]), False)),
        (r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",
         lambda m: (_dm(today, int(m[1]), int(m[2]), m[3]), False)),
        (r"\b(?:on\s+)?the\s+(\d{1,2})(?:st|nd|rd|th)\b|\bon\s+(\d{1,2})(?:st|nd|rd|th)\b",
         lambda m: (_day_of_month(today, int(m[1] or m[2])), False)),
        (r"\b(?:coming\s+)?" + WD + r"\b", lambda m: (_next_weekday(today, WEEKDAYS[m[1].lower()]), False)),
    ]
    for pattern, fn in rules:
        m = re.search(PREP + pattern, text, re.I)
        if m:
            d, vague = fn(m)
            if d:
                return d, _cut(text, m), vague
    return None, text, False


def _in_n(today: date, n_word: str, unit: str) -> date:
    n = _num(n_word.replace("a couple of", "couple of").replace("a few", "few")) or 1
    if unit.startswith("day"):
        return today + timedelta(days=n)
    if unit.startswith("week"):
        return today + timedelta(days=7 * n)
    return _add_months(today, n)


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _end_of_week(today: date) -> date:
    return _next_weekday(today, 4, include_today=True) if today.weekday() <= 4 else _next_weekday(today, 4)


def _next_week_day(today: date, wd: int) -> date:
    monday_next = today + timedelta(days=7 - today.weekday())
    return monday_next + timedelta(days=wd)


def _dm(today: date, d: int, m: int, y: str | None) -> date | None:
    if y:
        year = int(y) + (2000 if len(y) == 2 else 0)
        return _safe_date(year, m, d)
    candidate = _safe_date(today.year, m, d)
    if candidate and candidate < today - timedelta(days=1):
        candidate = _safe_date(today.year + 1, m, d)
    return candidate


def _day_of_month(today: date, d: int) -> date | None:
    candidate = _safe_date(today.year, today.month, d)
    if candidate and candidate >= today:
        return candidate
    nxt = _add_months(today.replace(day=1), 1)
    return _safe_date(nxt.year, nxt.month, d)


# ---- repeats ---------------------------------------------------------------------------------

def extract_repeat(text: str, today: date) -> tuple[str, str]:
    t = text
    rules = [
        (r"\b(?:every|each)\s+(?:day|morning|evening)\b|\bdaily\b|\beveryday\b", lambda m: "FREQ=DAILY"),
        (r"\b(?:every\s+weekday|on\s+weekdays|every\s+working\s+day|weekdays)\b",
         lambda m: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"),
        (r"\b(?:every|each)\s+(?:other|second|alternate)\s+" + WD + r"\b",
         lambda m: f"FREQ=WEEKLY;INTERVAL=2;BYDAY={DAY_CODES[WEEKDAYS[m[1].lower()]]}"),
        (r"\b(?:on\s+)?(?:the\s+)?(?:every|each)?\s*(first|1st|second|2nd|third|3rd|fourth|4th|last)\s+" + WD +
         r"\s+(?:of\s+)?(?:the\s+|every\s+|each\s+)?month\b",
         lambda m: f"FREQ=MONTHLY;BYDAY={ORDINAL_WORDS[m[1].lower()]}{DAY_CODES[WEEKDAYS[m[2].lower()]]}"),
        (r"\b(?:every|each)\s+(first|1st|second|2nd|third|3rd|fourth|4th|last)\s+" + WD + r"\b",
         lambda m: f"FREQ=MONTHLY;BYDAY={ORDINAL_WORDS[m[1].lower()]}{DAY_CODES[WEEKDAYS[m[2].lower()]]}"),
        (r"\b(?:every|each)\s+" + WD + r"s?\b|\bweekly\s+on\s+" + WD + r"s?\b|\bon\s+" + WD + r"s\b",
         lambda m: f"FREQ=WEEKLY;BYDAY={DAY_CODES[WEEKDAYS[(m[1] or m[2] or m[3]).lower()]]}"),
        (r"\b(?:every|each)\s+(\d+|two|three|four)\s+weeks\b",
         lambda m: f"FREQ=WEEKLY;INTERVAL={_num(m[1]) or 2}"),
        (r"\b(?:every|each)\s+(?:other|alternate)\s+week\b|\bfortnightly\b", lambda m: "FREQ=WEEKLY;INTERVAL=2"),
        (r"\b(?:every|each)\s+week\b|\bweekly\b", lambda m: "FREQ=WEEKLY"),
        (r"\b(?:on\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+of\s+(?:every|each|the)\s+month\b|"
         r"\b(?:every|each)\s+month\s+on\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\b|"
         r"\bmonthly\s+on\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\b",
         lambda m: f"FREQ=MONTHLY;BYMONTHDAY={int(m[1] or m[2] or m[3])}"),
        (r"\b(?:every|each)\s+(\d+|two|three|six)\s+months\b", lambda m: f"FREQ=MONTHLY;INTERVAL={_num(m[1]) or 2}"),
        (r"\bquarterly\b|\b(?:every|each)\s+quarter\b", lambda m: "FREQ=MONTHLY;INTERVAL=3"),
        (r"\b(?:every|each)\s+month\b|\bmonthly\b", lambda m: "FREQ=MONTHLY"),
        (r"\b(?:every|each)\s+year\b|\byearly\b|\bannually\b", lambda m: "FREQ=YEARLY"),
    ]
    for pattern, fn in rules:
        m = re.search(pattern, t, re.I)
        if m:
            return fn(m), _cut(t, m)
    return "", t


# ---- people, priority, baskets ---------------------------------------------------------------

def extract_person(text: str, people: list[str]) -> tuple[str, bool]:
    """Returns (name, sure). Known people match in any case; new names must be Capitalised."""
    low = text.lower()
    for p in sorted(people, key=len, reverse=True):
        if p and re.search(r"\b" + re.escape(p.lower()) + r"\b", low):
            return p.title(), True
    m = re.search(r"\b(?:mr|mrs|ms|dr)\.?\s+([A-Z][a-z]+)", text)
    if m:
        return m[1], True
    for m in re.finditer(r"\b(?:" + PERSON_TRIGGERS + r")\s+(?:the\s+|my\s+)?([A-Za-z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                         text, re.I):
        name = m[1]
        first = name.split()[0]
        if first.lower() in NOT_NAMES:
            continue
        if first.lower() in ROLE_WORDS:
            return first.title(), False
        if first[0].isupper():
            parts = [w for w in name.split() if w.lower() not in NOT_NAMES]
            return " ".join(parts), True
        if re.match(r"(?:follow|chase|remind|waiting)", m[0], re.I) and len(first) > 2:
            return first.title(), False  # "remind ravi to ..." typed in lowercase
    m = re.search(r"\b([A-Z][a-z]+)\s+(?:sir|madam|ji|garu|anna)\b", text)
    if m and m[1].lower() not in NOT_NAMES:
        return m[1], True
    return "", False


def extract_priority(text: str) -> tuple[str, str]:
    m = PRIORITY_HIGH.search(text)
    if m:
        return "high", _cut(text, m)
    m = PRIORITY_LOW.search(text)
    if m:
        return "low", _cut(text, m)
    return "normal", text


def basket_for(text: str, baskets: list[tuple[int, str]]) -> tuple[int | None, bool, str]:
    """Returns (basket_id, explicit, text). Explicit means the basket was named out loud."""
    for bid, name in baskets:
        first = re.escape(name.lower().split()[0].strip("&,"))
        m = re.search(r"\b(?:in(?:to)?|to|under|for|on)?\s*(?:the\s+|my\s+)?(?:" + re.escape(name.lower()) + r"|" +
                      first + r")\s+(?:basket|list|bucket)\b", text, re.I)
        if m:
            return bid, True, _cut(text, m)
    for key, rx in CATEGORY_RES.items():
        if rx.search(text):
            bid = _category_basket(key, baskets)
            if bid:
                return bid, False, text
    return _category_basket("work", baskets), False, text


def _category_basket(key: str, baskets: list[tuple[int, str]]) -> int | None:
    for bid, name in baskets:
        if any(h in name.lower() for h in CATEGORY_NAME_HINTS[key]):
            return bid
    return None


# ---- splitting and tidying ---------------------------------------------------------------------

def _starts_with_action(piece: str) -> bool:
    stripped = FILLER_RE.sub("", piece.strip()).strip().lower()
    word = re.split(r"\W+", stripped, maxsplit=1)[0] if stripped else ""
    starts_filler = bool(re.match(r"(remind me|i need|i have|need to|have to|remember|don'?t forget|i must|i should)",
                                  piece.strip().lower()))
    return starts_filler or word in ACTION_VERBS


def split_tasks(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    sentences = [s for s in re.split(r"(?<!\d)[.!?;]+(?!\d)\s*|\n+", text) if s and s.strip()]
    pieces: list[str] = []
    for s in sentences:
        parts = re.split(r",\s*(?:and\s+)?(?:then\s+|also\s+)?|\s+(?:and\s+then|and\s+also|and|also|then|plus)\s+",
                         s, flags=re.I)
        current = ""
        for part in parts:
            if not part.strip():
                continue
            if current and _starts_with_action(part):
                pieces.append(current)
                current = part
            elif current:
                joiner = ", " if re.search(r",\s*$", current) else " and "
                current = f"{current}{joiner}{part}"
            else:
                current = part
        if current:
            pieces.append(current)
    return [p.strip() for p in pieces if p.strip()]


def tidy_title(text: str) -> str:
    t = FILLER_RE.sub("", text.strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r"^(?:to|on|by|for|at|and)\s+", "", t, flags=re.I)
    t = re.sub(r"(?:\s+(?:on|by|at|for|and|to|the|before|till|until|due|of|in|around))+\s*$", "", t, flags=re.I)
    t = t.strip(" ,.;:-")
    return t[:1].upper() + t[1:] if t else t


def parse_task(piece: str, today: date, baskets: list[tuple[int, str]], people: list[str]) -> Draft | None:
    text = piece
    notes = ""
    m = re.search(r"\bnotes?\s*[:\-]\s*(.+)$", text, re.I)
    if m:
        notes, text = m[1].strip(), text[: m.start()].strip()
    checklist: list[str] = []
    m = re.search(r"\b(?:checklist|steps|items)\s*[:\-]\s*(.+)$", text, re.I)
    if m:
        checklist = [i.strip(" .") for i in re.split(r",|\band\b", m[1]) if i.strip(" .")]
        text = text[: m.start()].strip()

    guessed: list[str] = []
    rule, text = extract_repeat(text, today)
    due_time, text = extract_time(text)
    due_date, text, vague = extract_date(text, today)
    if rule and not due_date:
        from .recurrence import first_date
        due_date = first_date(rule, today)
        guessed.append("due_date")
    elif vague:
        guessed.append("due_date")
    if due_time and not due_date:
        due_date = today
    priority, text = extract_priority(text)
    person, sure = extract_person(piece, people)
    if person and not sure:
        guessed.append("person")
    waiting = bool(person) and bool(WAITING_RE.search(piece))
    basket_id, explicit, text = basket_for(text, baskets)
    if not explicit:
        guessed.append("basket")
    title = tidy_title(text)
    if len(title) < 2:
        return None
    return Draft(title=title, notes=notes, basket_id=basket_id, due_date=due_date, due_time=due_time,
                 priority=priority, person=person, waiting=waiting, repeat_rule=rule, checklist=checklist,
                 guessed=guessed)


# ---- commands --------------------------------------------------------------------------------

STOP = set("the a an my to for of on with and is are was be task item please it that this about re regarding "
           "up done complete completed finished closed mark as".split())


def _tokens(s: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", s.lower()):
        if w in STOP or len(w) < 2:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if len(w) > 4 and w.endswith(suffix):
                w = w[: -len(suffix)]
                break
        out.add(w)
    return out


def best_match(query: str, tasks: list[dict]) -> tuple[dict | None, float]:
    q = _tokens(query)
    if not q:
        return None, 0.0
    best, best_score = None, 0.0
    for t in tasks:
        tt = _tokens(t["title"]) | _tokens(t.get("person") or "")
        score = len(q & tt) / len(q)
        if score > best_score:
            best, best_score = t, score
    return best, best_score


COMPLETE_RES = [
    re.compile(r"^(?:please\s+)?(?:mark|tick|check\s+off|set)\s+(?:the\s+)?(?P<q>.+?)\s+(?:as\s+)?"
               r"(?:done|complete|completed|finished|closed)$", re.I),
    re.compile(r"^(?:i\s+)?(?:have\s+|'ve\s+|just\s+)*(?:done|finished|completed|closed)\s+(?:with\s+)?(?:the\s+)?(?P<q>.+)$", re.I),
    re.compile(r"^(?P<q>.+?)\s+(?:is|are|has been|have been)\s+(?:done|complete|completed|finished|closed|sorted|over)$", re.I),
    re.compile(r"^(?:done|finished)\s+with\s+(?:the\s+)?(?P<q>.+)$", re.I),
    re.compile(r"^(?:close|tick off|cross off)\s+(?:the\s+)?(?:task\s+)?(?P<q>.+)$", re.I),
]
RESCHEDULE_RE = re.compile(r"^(?:please\s+)?(?:move|push|postpone|reschedule|shift|defer|change)\s+(?:the\s+)?"
                           r"(?P<q>.+?)\s+(?:to|till|until|for)\s+(?P<when>.+)$", re.I)
QUERY_RE = re.compile(r"^(?:what(?:'s|s| is| are| do)?|which|show(?:\s+me)?|list|any(?:thing)?|do i have|"
                      r"how many|tell me|read out|give me)\b", re.I)


def interpret(text: str, *, today: date, now_time: time, baskets: list[tuple[int, str]], people: list[str],
              open_tasks: list[dict]) -> Interpretation:
    raw = re.sub(r"\s+", " ", text or "").strip()
    clean = FILLER_RE.sub("", raw).strip(" .!?") if not QUERY_RE.match(raw) else raw.strip(" .!?")
    if not clean:
        return Interpretation(intent="unclear", answer="I didn't catch anything. Try again?")

    if QUERY_RE.match(raw):
        return _query(raw, today, people, open_tasks, baskets)

    for rx in COMPLETE_RES:
        m = rx.match(clean)
        if m:
            target, score = best_match(m["q"], open_tasks)
            if target and score >= 0.5:
                return Interpretation(intent="complete", targets=[{"task_id": target["id"]}],
                                      answer=f"Mark “{target['title']}” as done?")
            if rx is not COMPLETE_RES[0] and rx is not COMPLETE_RES[3]:
                break  # might just be a sentence; treat as a new task below
            return Interpretation(intent="complete", answer=f"I couldn't find an open task like “{m['q']}”.")

    m = RESCHEDULE_RE.match(clean)
    if m:
        when_time, rest = extract_time(m["when"])
        when_date, _, _ = extract_date(rest, today)
        target, score = best_match(m["q"], open_tasks)
        if target and score >= 0.5 and (when_date or when_time):
            when_date = when_date or (date.fromisoformat(target["due_date"]) if target.get("due_date") else today)
            return Interpretation(
                intent="reschedule",
                targets=[{"task_id": target["id"], "due_date": when_date,
                          "due_time": when_time}],
                answer=f"Move “{target['title']}” to {when_date.strftime('%a %d %b')}"
                       + (f" at {when_time.strftime('%H:%M')}" if when_time else "") + "?",
            )

    drafts = [d for d in (parse_task(p, today, baskets, people) for p in split_tasks(raw)) if d]
    if not drafts:
        return Interpretation(intent="unclear", answer="I couldn't turn that into a task. Try again?")
    return Interpretation(intent="create", drafts=drafts[:15])


def _query(raw: str, today: date, people: list[str], open_tasks: list[dict],
           baskets: list[tuple[int, str]]) -> Interpretation:
    low = raw.lower()
    items = list(open_tasks)
    scope = "open"
    person, _ = extract_person(raw, people)
    if person:
        items = [t for t in items if t.get("person", "").lower() == person.lower()]
        scope = f"with {person}"
    if "overdue" in low or "late" in low:
        items = [t for t in items if t.get("overdue")]
        scope = "overdue" if not person else scope + ", overdue"
    elif "waiting" in low:
        items = [t for t in items if t.get("status") == "waiting"]
        scope = "you're waiting on" if not person else scope
    elif "tomorrow" in low:
        tmr = (today + timedelta(days=1)).isoformat()
        items = [t for t in items if t.get("due_date") == tmr]
        scope = "due tomorrow"
    elif "this week" in low:
        end = (today + timedelta(days=6 - today.weekday())).isoformat()
        items = [t for t in items if t.get("due_date") and t["due_date"] <= end]
        scope = "due this week"
    elif "today" in low or (not person and not any(n.lower() in low for _, n in baskets)):
        items = [t for t in items if t.get("due_date") and t["due_date"] <= today.isoformat()]
        scope = "due today or overdue"
    for bid, name in baskets:
        if name.lower().split()[0] in low:
            items = [t for t in items if t.get("basket_id") == bid]
            scope += f" in {name}"
            break
    if not items:
        return Interpretation(intent="query", answer=f"Nothing {scope}.")
    titles = [t["title"] for t in items[:5]]
    more = f", and {len(items) - 5} more" if len(items) > 5 else ""
    listing = ", ".join(titles[:-1]) + (" and " if len(titles) > 1 else "") + titles[-1]
    noun = "item" if len(items) == 1 else "items"
    return Interpretation(intent="query", answer=f"{len(items)} {noun} {scope}: {listing}{more}.",
                          match_ids=[t["id"] for t in items])
