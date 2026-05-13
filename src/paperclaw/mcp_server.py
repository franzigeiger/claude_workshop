"""MCP server — exposes PaperClaw as tools for Claude agents."""

import contextlib
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from paperclaw.agent.answer import answer as do_answer
from paperclaw.agent.anthropic_backend import AnthropicBackend
from paperclaw.ingest.pipeline import run as run_pipeline
from paperclaw.store.index import (
    add_document,
    default_embed,
    get_client,
    get_collection,
)

load_dotenv()

_DEFAULT_INBOX = "~/inbox"
_DEFAULT_LIBRARY = "~/Documents/paperclaw-library"
_DEFAULT_HOME = "~/.paperclaw"

mcp = FastMCP("paperclaw")


def _resolve(env_key: str, default: str, override: str | None) -> Path:
    return Path(override or os.environ.get(env_key, default)).expanduser()


def _chroma_path(home_override: str | None = None) -> Path:
    return _resolve("PAPERCLAW_HOME", _DEFAULT_HOME, home_override) / "chroma"


@mcp.tool()
def ingest(
    inbox: str | None = None,
    library: str | None = None,
) -> str:
    """Classify and file every PDF in the inbox folder into the library.

    Returns a summary of how many documents were added, skipped, or failed.
    Newly added documents are automatically indexed for search.
    """
    inbox_path = _resolve("PAPERCLAW_INBOX", _DEFAULT_INBOX, inbox)
    library_path = _resolve("PAPERCLAW_LIBRARY", _DEFAULT_LIBRARY, library)
    chroma = _chroma_path()

    if not inbox_path.is_dir():
        return f"error: inbox {inbox_path} is not a directory"

    try:
        backend = AnthropicBackend()
    except RuntimeError as exc:
        return f"error: {exc}"

    result = run_pipeline(inbox_path, library_path, backend)

    if result.added:
        collection = get_collection(get_client(chroma))
        for doc in result.documents:
            md_path = Path(doc.dest).with_suffix(".md")
            content = md_path.read_text(encoding="utf-8")
            parts = content.split("---\n", 2)
            if len(parts) < 3:
                continue
            frontmatter: dict[str, object] = yaml.safe_load(parts[1]) or {}
            text = parts[2].strip()
            doc_id = str(md_path.relative_to(library_path).with_suffix(""))
            doc_date: str = str(frontmatter.get("doc_date") or "")
            metadata: dict[str, str | int | float | bool] = {
                "kind": str(frontmatter.get("kind") or "other"),
                "topic": str(frontmatter.get("topic") or ""),
                "doc_date": doc_date,
                "year": doc_date[:4] if len(doc_date) >= 4 else "",
                "issuer": str(frontmatter.get("issuer") or ""),
                "confidence": float(str(frontmatter.get("confidence") or "0.0")),
                "needs_review": bool(frontmatter.get("needs_review")),
                "source_pdf": str(frontmatter.get("source_pdf") or ""),
            }
            add_document(collection, doc_id, text, metadata, default_embed)

    return (
        f"{result.total} PDF(s) found, "
        f"{result.added} added, {result.skipped} skipped, {result.failed} failed."
    )


@mcp.tool()
def ask(
    question: str,
    k: int = 5,
    kind: str | None = None,
    topic: str | None = None,
    year: str | None = None,
) -> str:
    """Answer a natural-language question about the document library.

    Optionally filter by document kind (e.g. 'invoice', 'notice'),
    topic (e.g. 'utility', 'tax'), or year (e.g. '2024').
    Returns the answer followed by the source document IDs consulted.
    """
    try:
        backend = AnthropicBackend()
    except RuntimeError as exc:
        return f"error: {exc}"

    filters: dict[str, str] = {}
    if kind:
        filters["kind"] = kind
    if topic:
        filters["topic"] = topic
    if year:
        filters["year"] = year

    collection = get_collection(get_client(_chroma_path()))
    result = do_answer(question, collection, backend, default_embed, k=k, filters=filters or None)

    if result.sources:
        sources = "\n".join(f"  {s}" for s in result.sources)
        return f"{result.answer}\n\nSources:\n{sources}"
    return result.answer


@mcp.tool()
def reindex(library: str | None = None, from_scratch: bool = False) -> str:
    """Rebuild the search index from all .md transcripts in the library.

    Use from_scratch=True to drop and fully rebuild the index (e.g. after
    manually editing transcripts or moving the library).
    """
    library_path = _resolve("PAPERCLAW_LIBRARY", _DEFAULT_LIBRARY, library)
    chroma = _chroma_path()

    client = get_client(chroma)
    if from_scratch:
        with contextlib.suppress(Exception):
            client.delete_collection("paperclaw")
    collection = get_collection(client)

    md_files = sorted(library_path.rglob("*.md"))
    count = 0
    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        if len(parts) < 3:
            continue
        frontmatter: dict[str, object] = yaml.safe_load(parts[1]) or {}
        text = parts[2].strip()
        doc_id = str(md_path.relative_to(library_path).with_suffix(""))
        doc_date: str = str(frontmatter.get("doc_date") or "")
        metadata: dict[str, str | int | float | bool] = {
            "kind": str(frontmatter.get("kind") or "other"),
            "topic": str(frontmatter.get("topic") or ""),
            "doc_date": doc_date,
            "year": doc_date[:4] if len(doc_date) >= 4 else "",
            "issuer": str(frontmatter.get("issuer") or ""),
            "confidence": float(str(frontmatter.get("confidence") or "0.0")),
            "needs_review": bool(frontmatter.get("needs_review")),
            "source_pdf": str(frontmatter.get("source_pdf") or ""),
        }
        add_document(collection, doc_id, text, metadata, default_embed)
        count += 1

    return f"Indexed {count} document(s) from {library_path} into {chroma}."


def main() -> None:
    mcp.run()
