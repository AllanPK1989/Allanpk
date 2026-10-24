"""Optional embeddings: hybrid retrieval with a fake OpenAI-compatible embeddings server."""
import httpx

from app import embeddings, retrieval
from app.config import get_config
from app.db import SessionLocal
from app.indexing import reindex_all
from app.machines_service import get_machine

# A tiny "model": synonyms share a dimension, so "stuck" lands near "not returning".
DIMS = [("cylinder",), ("return", "returning", "stuck", "jammed"), ("coil", "solenoid"), ("label", "print"), ("air", "pressure")]


def fake_post(texts):
    out = []
    for text in texts:
        words = text.lower().replace(",", " ").replace(".", " ").split()
        out.append([float(sum(1 for w in words if w in dim)) + 0.01 for dim in DIMS])
    return out


def enable(monkeypatch, post=fake_post):
    cfg = get_config()
    monkeypatch.setattr(cfg, "embeddings_provider", "openai_compat")
    monkeypatch.setattr(cfg, "embeddings_base_url", "http://embed.test/v1")
    monkeypatch.setattr(embeddings, "_post", post)
    embeddings._query_vector.cache_clear()


def test_disabled_by_default(db_session):
    assert not embeddings.enabled()
    assert embeddings.similarities(db_session, "anything", [("log", 1)]) is None


def test_vectors_find_synonyms_that_keywords_miss(db_session, monkeypatch):
    machine = get_machine(db_session, "DEMO-SF-01")
    query = "cylinder stuck"
    keyword_only = {i.ref: i.score for i in retrieval.build_context(db_session, machine, query).items}
    enable(monkeypatch)
    with SessionLocal() as db:
        counts = reindex_all(db)
        db.commit()
        assert counts["logs"] == 7 and counts["cards"] == 1 and counts["chunks"] >= 4
        assert reindex_all(db)["logs"] == 0  # unchanged text is not embedded again
        hybrid = {i.ref: i.score for i in retrieval.build_context(db, get_machine(db, "DEMO-SF-01"), query).items}
    log3 = "LOG-" + next(r for r in hybrid if r.startswith("LOG-")).split("LOG-")[1]
    assert hybrid[log3] > keyword_only.get(log3, 0)


def test_provider_failure_falls_back_to_keywords(db_session, monkeypatch):
    def broken(texts):
        raise httpx.ConnectError("down")

    enable(monkeypatch, broken)
    machine = get_machine(db_session, "DEMO-SF-01")
    items = retrieval.build_context(db_session, machine, "Cylinder return aagala").items
    assert any(i.kind == "fault_card" for i in items)
