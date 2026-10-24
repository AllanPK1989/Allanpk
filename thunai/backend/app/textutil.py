"""Small text helpers: language detection, tokenising and keyword similarity.

Phase 1 retrieval is keyword based (TF-IDF cosine) because every search is first narrowed to one
machine or machine type, so the candidate sets are small. Phase 2 adds vector embeddings.
"""
import math
import re
from collections import Counter

TAMIL = re.compile(r"[஀-௿]")
LATIN = re.compile(r"[A-Za-z]")
TOKEN = re.compile(r"[a-z0-9]+|[஀-௿]+")

STOPWORDS = set(
    """a an the and or of to in on at for with is are was were be been it this that by from as
    not no yes ok but if then so do does did done has have had will would can could should
    machine problem issue please check checked""".split()
)


def detect_lang(text: str) -> str:
    """'ta' for Tamil script, 'mixed' for Tamil script plus Latin words, else 'en'.

    Romanised Tamil ("coil maathiten") is reported as 'en'; the AI handles it.
    """
    has_ta = bool(TAMIL.search(text or ""))
    has_en = bool(LATIN.search(text or ""))
    if has_ta and has_en:
        return "mixed"
    return "ta" if has_ta else "en"


def normalise(text: str, variants: dict[str, str] | None = None) -> str:
    """Lower-case and replace spoken variants with the glossary's English term."""
    out = (text or "").lower()
    for spoken, term in sorted((variants or {}).items(), key=lambda kv: -len(kv[0])):
        if spoken:
            out = re.sub(rf"(?<!\w){re.escape(spoken.lower())}(?!\w)", term.lower(), out)
    return out


def stem(token: str) -> str:
    """Very light English stemming so "returning" matches "return" and "sensors" matches "sensor"."""
    if not token.isascii() or len(token) <= 4:
        return token
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def tokens(text: str, variants: dict[str, str] | None = None) -> list[str]:
    return [stem(t) for t in TOKEN.findall(normalise(text, variants)) if t not in STOPWORDS and len(t) > 1]


def overlap_ratio(part: str, whole: str) -> float:
    """Share of the tokens in `part` that also appear in `whole` (1.0 when part is empty)."""
    p = tokens(part)
    if not p:
        return 1.0
    w = set(tokens(whole))
    return sum(1 for t in p if t in w) / len(p)


def rank(query: str, docs: list[str], variants: dict[str, str] | None = None) -> list[float]:
    """TF-IDF cosine similarity of the query against each doc (0..1)."""
    doc_tokens = [tokens(d, variants) for d in docs]
    q_tokens = tokens(query, variants)
    if not q_tokens or not docs:
        return [0.0] * len(docs)
    n = len(docs) + 1
    df = Counter()
    for toks in doc_tokens + [q_tokens]:
        df.update(set(toks))

    def vec(toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        return {t: (c / len(toks)) * (math.log((1 + n) / (1 + df[t])) + 1) for t, c in tf.items()}

    qv = vec(q_tokens)
    qn = math.sqrt(sum(v * v for v in qv.values()))
    scores = []
    for toks in doc_tokens:
        if not toks:
            scores.append(0.0)
            continue
        dv = vec(toks)
        dn = math.sqrt(sum(v * v for v in dv.values()))
        dot = sum(qv[t] * dv.get(t, 0.0) for t in qv)
        scores.append(round(dot / (qn * dn), 4) if qn and dn else 0.0)
    return scores
