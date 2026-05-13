from typing import cast

import chromadb
import pytest

from paperclaw.agent.answer import AnswerResult, answer
from paperclaw.store.index import SearchResult


class FakeBackend:
    def __init__(self, reply: str = "The answer is 42.") -> None:
        self._reply = reply
        self.last_user: str = ""

    def chat(self, system: str, user: str, **_: object) -> str:
        self.last_user = user
        return self._reply


def _fake_embed(texts: list[str]) -> list[list[float]]:
    return [[0.1] * 16 for _ in texts]


def _fake_collection() -> chromadb.Collection:
    return cast(chromadb.Collection, object())


def _fake_result(doc_id: str = "invoices/2024/bill") -> SearchResult:
    return SearchResult(
        doc_id=doc_id,
        text="Electricity invoice for Q3 2024.",
        distance=0.1,
        metadata={
            "kind": "invoice",
            "topic": "utility",
            "doc_date": "2024-11-03",
            "year": "2024",
            "issuer": "Stadtwerke München",
            "confidence": 0.95,
            "needs_review": False,
            "source_pdf": "/inbox/bill.pdf",
        },
    )


def test_answer_returns_answer_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "paperclaw.agent.answer.query",
        lambda *a, **kw: [_fake_result()],
    )
    result = answer("What is my electricity bill?", _fake_collection(), FakeBackend(), _fake_embed)
    assert isinstance(result, AnswerResult)
    assert result.answer == "The answer is 42."


def test_answer_includes_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "paperclaw.agent.answer.query",
        lambda *a, **kw: [_fake_result("invoices/2024/bill")],
    )
    result = answer("electricity", _fake_collection(), FakeBackend(), _fake_embed)
    assert "invoices/2024/bill" in result.sources


def test_answer_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("paperclaw.agent.answer.query", lambda *a, **kw: [])
    result = answer("anything", _fake_collection(), FakeBackend(), _fake_embed)
    assert result.sources == []
    assert "No relevant documents" in result.answer


def test_answer_passes_filters_to_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _capture(*args: object, **kwargs: object) -> list[SearchResult]:
        captured.update(kwargs)
        return [_fake_result()]

    monkeypatch.setattr("paperclaw.agent.answer.query", _capture)
    answer("question", _fake_collection(), FakeBackend(), _fake_embed, filters={"kind": "invoice"})
    assert captured.get("filters") == {"kind": "invoice"}


def test_answer_truncates_long_text_to_4000_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    long_result = SearchResult(
        doc_id="invoices/2024/big",
        text="x" * 6000,
        distance=0.1,
        metadata={
            "kind": "invoice",
            "topic": "",
            "doc_date": "",
            "year": "",
            "issuer": "",
            "confidence": 0.9,
            "needs_review": False,
            "source_pdf": "",
        },
    )
    monkeypatch.setattr("paperclaw.agent.answer.query", lambda *a, **kw: [long_result])
    backend = FakeBackend()
    answer("question", _fake_collection(), backend, _fake_embed)
    assert "x" * 4000 in backend.last_user
    assert "x" * 4001 not in backend.last_user
