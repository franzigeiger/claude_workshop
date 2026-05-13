from pathlib import Path

from paperclaw.ingest.classify import Classification
from paperclaw.store.library import dest_path, dest_stem, slug, write


def _classification(**overrides: object) -> Classification:
    defaults: dict[str, object] = {
        "kind": "invoice",
        "topic": "utility",
        "doc_date": "2024-11-03",
        "issuer": "Stadtwerke München",
        "short_desc": "strom-q3",
        "summary": "Electricity invoice for Q3 2024.",
        "confidence": 0.95,
        "notes": "",
    }
    defaults.update(overrides)
    return Classification(**defaults)


# --- slug ---


def test_slug_lowercases() -> None:
    assert slug("HELLO WORLD") == "hello-world"


def test_slug_removes_special_chars() -> None:
    # Unicode word chars (umlauts) are preserved — fine for German filenames
    assert slug("Stadtwerke München GmbH & Co.") == "stadtwerke-münchen-gmbh-co"


def test_slug_collapses_spaces() -> None:
    assert slug("foo   bar") == "foo-bar"


def test_slug_empty_falls_back() -> None:
    assert slug("!!!") == "unknown"


# --- dest_stem ---


def test_dest_stem_normal() -> None:
    stem = dest_stem(_classification())
    assert stem == "2024-11-03__invoice__stadtwerke-münchen__strom-q3"


def test_dest_stem_no_date() -> None:
    stem = dest_stem(_classification(doc_date=None))
    assert stem.startswith("unknown__invoice__")


def test_dest_stem_no_issuer() -> None:
    stem = dest_stem(_classification(issuer=None))
    assert "__unknown__" in stem


# --- dest_path ---


def test_dest_path_structure(tmp_path: Path) -> None:
    c = _classification()
    path = dest_path(c, tmp_path)
    # …/invoices/2024/<stem>.pdf
    assert path.parts[-3] == "invoices"
    assert path.parts[-2] == "2024"
    assert path.suffix == ".pdf"


def test_dest_path_unknown_year(tmp_path: Path) -> None:
    c = _classification(doc_date=None)
    path = dest_path(c, tmp_path)
    assert "unknown-year" in str(path)


# --- write ---


def test_write_creates_pdf_and_transcript(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    lib = tmp_path / "library"

    c = _classification()
    dest = write(src, "extracted text here", c, lib)

    assert dest.exists()
    assert dest.suffix == ".pdf"
    transcript = dest.with_suffix(".md")
    assert transcript.exists()
    content = transcript.read_text()
    assert "kind: invoice" in content
    assert "extracted text here" in content


def test_write_is_idempotent(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    lib = tmp_path / "library"

    c = _classification()
    dest1 = write(src, "text", c, lib)
    dest2 = write(src, "text", c, lib)

    assert dest1 == dest2
    # Only one file should exist (no _1 suffix)
    pdfs = list(lib.rglob("*.pdf"))
    assert len(pdfs) == 1


def test_write_transcript_flags_low_confidence(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    lib = tmp_path / "library"

    c = _classification(confidence=0.4)
    dest = write(src, "text", c, lib)
    content = dest.with_suffix(".md").read_text()
    assert "needs_review: true" in content
