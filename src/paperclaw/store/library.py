import logging
import re
import shutil
from pathlib import Path

import yaml

from paperclaw.ingest.classify import Classification, load_taxonomy

log = logging.getLogger(__name__)

_LOW_CONFIDENCE = 0.6


def slug(text: str) -> str:
    """Convert free text to a lowercase hyphen-separated identifier slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "unknown"


def _kind_folder(kind: str) -> str:
    taxonomy = load_taxonomy()
    return taxonomy["kinds"].get(kind, f"{kind}s")


def _year(doc_date: str | None) -> str:
    if doc_date and len(doc_date) >= 4 and doc_date[:4].isdigit():
        return doc_date[:4]
    return "unknown-year"


def dest_stem(c: Classification) -> str:
    date = c.doc_date or "unknown"
    issuer = slug(c.issuer or "unknown")
    desc = slug(c.short_desc or "document")
    return f"{date}__{c.kind}__{issuer}__{desc}"


def dest_path(c: Classification, library: Path) -> Path:
    return library / _kind_folder(c.kind) / _year(c.doc_date) / f"{dest_stem(c)}.pdf"


def _write_transcript(
    dest_pdf: Path,
    text: str,
    c: Classification,
    source_pdf: Path,
) -> None:
    frontmatter: dict[str, object] = {
        "kind": c.kind,
        "topic": c.topic,
        "doc_date": c.doc_date,
        "issuer": c.issuer,
        "short_desc": c.short_desc,
        "summary": c.summary,
        "confidence": c.confidence,
        "notes": c.notes,
        "needs_review": c.confidence < _LOW_CONFIDENCE,
        "source_pdf": str(source_pdf),
    }
    dest_pdf.with_suffix(".md").write_text(
        f"---\n{yaml.dump(frontmatter, allow_unicode=True)}---\n\n{text}\n",
        encoding="utf-8",
    )


def write(pdf_src: Path, text: str, c: Classification, library: Path) -> Path:
    """Copy PDF and write .md transcript to the library. Returns destination path."""
    dest = dest_path(c, library)
    if dest.exists():
        log.debug("Already in library, skipping: %s", dest.relative_to(library))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_src, dest)
    _write_transcript(dest, text, c, pdf_src)
    if c.confidence < _LOW_CONFIDENCE:
        log.warning("Low confidence %.2f for %s — flagged for review", c.confidence, dest.name)
    log.info("Filed %s → %s", pdf_src.name, dest.relative_to(library))
    return dest
