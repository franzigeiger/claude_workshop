from pathlib import Path

import chromadb

from paperclaw.store.index import SearchResult, add_document, get_collection, query


def _fake_embed(texts: list[str]) -> list[list[float]]:
    dim = 16
    return [[float(abs(hash(t)) % 100) / 100.0] * dim for t in texts]


def _make_collection(tmp_path: Path) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    return get_collection(client)


def _meta() -> dict[str, str | int | float | bool]:
    return {
        "kind": "invoice",
        "topic": "utility",
        "doc_date": "2024-11-03",
        "year": "2024",
        "issuer": "Stadtwerke München",
        "confidence": 0.95,
        "needs_review": False,
        "source_pdf": "/inbox/bill.pdf",
    }


def test_add_and_query_returns_result(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    add_document(col, "invoices/2024/bill", "electricity invoice Q3", _meta(), _fake_embed)
    results = query(col, "electricity bill", k=1, filters=None, embed_fn=_fake_embed)
    assert len(results) == 1
    assert results[0].doc_id == "invoices/2024/bill"


def test_query_returns_search_result_type(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    add_document(col, "doc1", "some text", _meta(), _fake_embed)
    results = query(col, "text", k=1, filters=None, embed_fn=_fake_embed)
    assert isinstance(results[0], SearchResult)


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    add_document(col, "doc1", "original text", _meta(), _fake_embed)
    add_document(col, "doc1", "updated text", _meta(), _fake_embed)
    results = query(col, "text", k=5, filters=None, embed_fn=_fake_embed)
    ids = [r.doc_id for r in results]
    assert ids.count("doc1") == 1
    assert results[0].text == "updated text"


def test_query_with_filter(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    invoice_meta = _meta()
    letter_meta = dict(_meta())
    letter_meta["kind"] = "letter"
    add_document(col, "doc-invoice", "invoice text", invoice_meta, _fake_embed)
    add_document(col, "doc-letter", "letter text", letter_meta, _fake_embed)
    results = query(col, "document", k=5, filters={"kind": "invoice"}, embed_fn=_fake_embed)
    assert all(r.doc_id == "doc-invoice" for r in results)


def test_query_empty_collection(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    results = query(col, "anything", k=5, filters=None, embed_fn=_fake_embed)
    assert results == []
