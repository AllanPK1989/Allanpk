"""Optional vector similarity (SPEC.md 11.5).

Off by default: Anthropic has no embeddings API, and another vendor would need the data-location
approval in SPEC question 6. Set EMBEDDINGS_PROVIDER=openai_compat and EMBEDDINGS_BASE_URL to any
server with an OpenAI-style `POST /embeddings` endpoint (for example a multilingual model on the
plant network). Vectors are stored as JSON in the `embeddings` table and compared in Python: every
search is first narrowed to one machine or machine type, so candidate sets are small.
"""
import hashlib
import logging
import math
from functools import lru_cache

import httpx
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from .config import get_config
from .models import Embedding

log = logging.getLogger("thunai.embeddings")
BATCH = 64


def enabled() -> bool:
    cfg = get_config()
    return cfg.embeddings_provider == "openai_compat" and bool(cfg.embeddings_base_url)


def _post(texts: list[str]) -> list[list[float]]:
    cfg = get_config()
    headers = {"Authorization": f"Bearer {cfg.embeddings_api_key}"} if cfg.embeddings_api_key else {}
    response = httpx.post(
        cfg.embeddings_base_url.rstrip("/") + "/embeddings",
        json={"model": cfg.embeddings_model, "input": texts},
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    data = sorted(response.json()["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in data]


def embed(texts: list[str]) -> list[list[float]] | None:
    """Vectors for the texts, or None when the provider is off or unreachable (keyword search continues)."""
    if not enabled() or not texts:
        return None
    try:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            out.extend(_post([t[:4000] for t in texts[i : i + BATCH]]))
        return out
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning("Embeddings unavailable: %s", e)
        return None


@lru_cache(maxsize=256)
def _query_vector(text: str) -> tuple[float, ...] | None:
    vectors = embed([text])
    return tuple(vectors[0]) if vectors else None


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def store(db: Session, items: list[tuple[str, int, str]]) -> int:
    """Embed (source_type, source_id, text) items whose text changed since the last run."""
    if not enabled() or not items:
        return 0
    model = get_config().embeddings_model
    keys = [(t, i) for t, i, _ in items]
    existing = {
        (e.source_type, e.source_id): e
        for e in db.scalars(
            select(Embedding).where(Embedding.model == model, tuple_(Embedding.source_type, Embedding.source_id).in_(keys))
        )
    }
    todo = [(t, i, text) for t, i, text in items if text.strip() and (existing.get((t, i)) is None or existing[(t, i)].text_hash != _hash(text))]
    vectors = embed([text for _, _, text in todo]) if todo else []
    if vectors is None:
        return 0
    for (t, i, text), vector in zip(todo, vectors):
        row = existing.get((t, i))
        if row is None:
            db.add(Embedding(source_type=t, source_id=i, model=model, vector=vector, text_hash=_hash(text)))
        else:
            row.vector, row.text_hash = vector, _hash(text)
    return len(todo)


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return max(0.0, dot / (na * nb)) if na and nb else 0.0


def similarities(db: Session, query: str, keys: list[tuple[str, int]]) -> list[float | None] | None:
    """Cosine similarity of the query to each stored vector (None where a record has no vector yet)."""
    if not enabled() or not keys or not query.strip():
        return None
    qv = _query_vector(query.strip())
    if qv is None:
        return None
    model = get_config().embeddings_model
    vectors = {
        (e.source_type, e.source_id): e.vector
        for e in db.scalars(
            select(Embedding).where(Embedding.model == model, tuple_(Embedding.source_type, Embedding.source_id).in_(keys))
        )
    }
    return [round(_cosine(qv, vectors[k]), 4) if k in vectors else None for k in keys]
