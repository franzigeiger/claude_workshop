from pathlib import Path

import pytest

from paperclaw.ingest.classify import Classification
from paperclaw.ingest.pipeline import IngestResult, run


def _make_classification(**overrides: object) -> Classification:
    defaults: dict[str, object] = {
        "kind": "invoice",
        "topic": "utility",
        "doc_date": "2024-11-03",
        "issuer": "Stadtwerke München",
        "short_desc": "strom-q3",
        "summary": "Electricity bill.",
        "confidence": 0.9,
        "notes": "",
    }
    defaults.update(overrides)
    return Classification(**defaults)


class FakeBackend:
    def __init__(self, classification: Classification) -> None:
        self._classification = classification

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        return self._classification.model_dump_json()


def _stub_extract(path: Path) -> str:
    return f"extracted text from {path.name}"


def test_run_adds_new_pdfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    lib = tmp_path / "library"
    (inbox / "bill.pdf").write_bytes(b"%PDF fake")

    monkeypatch.setattr("paperclaw.ingest.pipeline.extract_text", _stub_extract)
    backend = FakeBackend(_make_classification())

    result = run(inbox, lib, backend)

    assert result.total == 1
    assert result.added == 1
    assert result.skipped == 0
    assert result.failed == 0
    assert len(result.documents) == 1


def test_run_skips_already_filed_pdfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    lib = tmp_path / "library"
    (inbox / "bill.pdf").write_bytes(b"%PDF fake")

    monkeypatch.setattr("paperclaw.ingest.pipeline.extract_text", _stub_extract)
    backend = FakeBackend(_make_classification())

    run(inbox, lib, backend)
    result2 = run(inbox, lib, backend)

    assert result2.skipped == 1
    assert result2.added == 0


def test_run_handles_extract_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    lib = tmp_path / "library"
    (inbox / "broken.pdf").write_bytes(b"not a pdf")

    def _failing_extract(path: Path) -> str:
        raise RuntimeError("PDF parse error")

    monkeypatch.setattr("paperclaw.ingest.pipeline.extract_text", _failing_extract)
    backend = FakeBackend(_make_classification())

    result = run(inbox, lib, backend)

    assert result.failed == 1
    assert result.added == 0


def test_run_empty_inbox(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    lib = tmp_path / "library"
    backend = FakeBackend(_make_classification())

    result = run(inbox, lib, backend)

    assert result.total == 0
    assert isinstance(result, IngestResult)
