import logging
from dataclasses import dataclass, field
from pathlib import Path

from paperclaw.agent.backend import LLMBackend
from paperclaw.ingest.classify import classify
from paperclaw.ingest.extract import extract_text
from paperclaw.store import library

log = logging.getLogger(__name__)


@dataclass
class DocRecord:
    source: str
    dest: str
    kind: str
    topic: str | None
    doc_date: str | None
    confidence: float
    needs_review: bool


@dataclass
class IngestResult:
    total: int = 0
    added: int = 0
    skipped: int = 0
    failed: int = 0
    documents: list[DocRecord] = field(default_factory=list)


def run(inbox: Path, lib: Path, backend: LLMBackend) -> IngestResult:
    """Process all PDFs in inbox, write classified results to the library."""
    pdfs = sorted(inbox.glob("*.pdf"))
    result = IngestResult(total=len(pdfs))

    for pdf in pdfs:
        try:
            text = extract_text(pdf)
            classification = classify(text, backend)
        except Exception as exc:
            log.warning("Failed to process %s: %s", pdf.name, exc)
            result.failed += 1
            continue

        dest = library.dest_path(classification, lib)
        if dest.exists():
            result.skipped += 1
            log.debug("Already in library: %s", dest.name)
            continue

        try:
            library.write(pdf, text, classification, lib)
        except Exception as exc:
            log.warning("Failed to write %s to library: %s", pdf.name, exc)
            result.failed += 1
            continue

        result.added += 1
        result.documents.append(
            DocRecord(
                source=str(pdf),
                dest=str(dest),
                kind=classification.kind,
                topic=classification.topic,
                doc_date=classification.doc_date,
                confidence=classification.confidence,
                needs_review=classification.confidence < 0.6,
            )
        )

    return result
