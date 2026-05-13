import logging
from pathlib import Path

import pypdf

log = logging.getLogger(__name__)

_MIN_CHARS = 100
_MIN_PRINTABLE_RATIO = 0.8


def _is_usable(text: str) -> bool:
    """Return True if the text layer looks like real document content."""
    if len(text) < _MIN_CHARS:
        return False
    printable = sum(1 for c in text if c.isprintable())
    return printable / len(text) >= _MIN_PRINTABLE_RATIO


def _extract_text_layer(path: Path) -> str:
    reader = pypdf.PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            parts.append(extracted)
    return "\n".join(parts)


def _extract_ocr(path: Path) -> str:
    try:
        import pdf2image  # type: ignore[import-not-found]  # noqa: PLC0415
        import pytesseract  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "OCR dependencies are not installed. "
            "Run: pip install 'paperclaw[ocr]' and ensure tesseract is on your PATH."
        ) from exc

    images = pdf2image.convert_from_path(path)
    parts: list[str] = []
    for img in images:
        parts.append(pytesseract.image_to_string(img, lang="deu+eng"))
    return "\n".join(parts)


def extract_text(path: Path) -> str:
    """Extract plain text from a PDF — text layer first, OCR fallback."""
    text = _extract_text_layer(path)
    if _is_usable(text):
        return text
    log.warning("Text layer too thin for %s — attempting OCR", path.name)
    return _extract_ocr(path)
