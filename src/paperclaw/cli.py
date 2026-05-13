import contextlib
import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
import yaml
from dotenv import load_dotenv

from paperclaw.agent.answer import answer as do_answer
from paperclaw.agent.anthropic_backend import AnthropicBackend
from paperclaw.ingest.pipeline import run as run_pipeline
from paperclaw.store.index import (
    add_document,
    default_embed,
    get_client,
    get_collection,
)

app = typer.Typer(name="paperclaw", no_args_is_help=True, add_completion=False)
log = logging.getLogger(__name__)

_DEFAULT_INBOX = "~/inbox"
_DEFAULT_LIBRARY = "~/Documents/paperclaw-library"
_DEFAULT_HOME = "~/.paperclaw"


def _resolve(env_key: str, default: str, override: Path | None) -> Path:
    return override or Path(os.environ.get(env_key, default)).expanduser()


@app.callback()
def _setup(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s", level=level)


@app.command()
def ingest(
    inbox: Annotated[
        Path | None,
        typer.Argument(help="Folder of PDFs to classify. Defaults to PAPERCLAW_INBOX or ~/inbox."),
    ] = None,
    library: Annotated[
        Path | None,
        typer.Option(
            "--library", "-l", help="Library root. Defaults to PAPERCLAW_LIBRARY or ~/library."
        ),
    ] = None,
) -> None:
    """Extract and classify every PDF in INBOX, writing results to the library."""
    load_dotenv()
    inbox_path = _resolve("PAPERCLAW_INBOX", _DEFAULT_INBOX, inbox)
    library_path = _resolve("PAPERCLAW_LIBRARY", _DEFAULT_LIBRARY, library)

    if not inbox_path.is_dir():
        typer.echo(f"error: inbox {inbox_path} is not a directory", err=True)
        raise typer.Exit(2)

    try:
        backend = AnthropicBackend()
    except RuntimeError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    result = run_pipeline(inbox_path, library_path, backend)
    typer.echo(
        f"Done: {result.total} PDF(s) found, "
        f"{result.added} added, {result.skipped} skipped, {result.failed} failed."
    )
    if result.failed:
        raise typer.Exit(4)


@app.command()
def reindex(
    library: Annotated[
        Path | None,
        typer.Option(
            "--library", "-l", help="Library root. Defaults to PAPERCLAW_LIBRARY or ~/library."
        ),
    ] = None,
    home: Annotated[
        Path | None,
        typer.Option(
            "--home", help="paperclaw data dir. Defaults to PAPERCLAW_HOME or ~/.paperclaw."
        ),
    ] = None,
    from_scratch: bool = typer.Option(False, "--from-scratch", help="Drop and rebuild the index."),
) -> None:
    """Rebuild the Chroma search index from all .md transcripts in the library."""
    load_dotenv()
    library_path = _resolve("PAPERCLAW_LIBRARY", _DEFAULT_LIBRARY, library)
    home_path = _resolve("PAPERCLAW_HOME", _DEFAULT_HOME, home)
    chroma_path = home_path / "chroma"

    client = get_client(chroma_path)
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
            log.warning("Skipping %s — no frontmatter", md_path.name)
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

    typer.echo(f"Indexed {count} document(s) into {chroma_path}.")


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Natural-language question about the library.")],
    k: Annotated[int, typer.Option("--k", help="Number of documents to retrieve.")] = 5,
    kind: Annotated[str | None, typer.Option("--kind", help="Filter by document kind.")] = None,
    topic: Annotated[str | None, typer.Option("--topic", help="Filter by topic.")] = None,
    year: Annotated[str | None, typer.Option("--year", help="Filter by year (e.g. 2024).")] = None,
    home: Annotated[
        Path | None,
        typer.Option(
            "--home", help="paperclaw data dir. Defaults to PAPERCLAW_HOME or ~/.paperclaw."
        ),
    ] = None,
) -> None:
    """Answer a natural-language question about the document library."""
    load_dotenv()
    chroma_path = _resolve("PAPERCLAW_HOME", _DEFAULT_HOME, home) / "chroma"

    filters: dict[str, str] = {}
    if kind:
        filters["kind"] = kind
    if topic:
        filters["topic"] = topic
    if year:
        filters["year"] = year

    try:
        backend = AnthropicBackend()
    except RuntimeError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    collection = get_collection(get_client(chroma_path))
    result = do_answer(question, collection, backend, default_embed, k=k, filters=filters or None)

    typer.echo(result.answer)
    if result.sources:
        typer.echo("\nSources:")
        for src in result.sources:
            typer.echo(f"  {src}")


@app.command()
def doctor() -> None:
    """Check that the environment is ready to run paperclaw."""
    load_dotenv()
    issues: list[str] = []

    if not os.environ.get("ANTHROPIC_API_KEY"):
        issues.append("ANTHROPIC_API_KEY is not set (required for the anthropic backend)")

    if shutil.which("tesseract") is None:
        issues.append("tesseract not found on PATH (OCR will be unavailable)")

    if issues:
        for msg in issues:
            typer.echo(f"  ✗ {msg}")
        raise typer.Exit(1)

    typer.echo("  ✓ All checks passed")
