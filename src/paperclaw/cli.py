import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

app = typer.Typer(name="paperclaw", no_args_is_help=True, add_completion=False)
log = logging.getLogger(__name__)


@app.callback()
def _setup(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s", level=level)


@app.command()
def ingest(
    inbox: Annotated[
        Path, typer.Argument(help="Folder of PDFs to classify and move to the library.")
    ],
) -> None:
    """Extract and classify every PDF in INBOX."""
    if not inbox.is_dir():
        typer.echo(f"error: {inbox} is not a directory", err=True)
        raise typer.Exit(2)
    pdfs = list(inbox.glob("*.pdf"))
    if not pdfs:
        typer.echo(f"No PDFs found in {inbox}.", err=True)
        raise typer.Exit(3)
    typer.echo(f"Found {len(pdfs)} PDF(s) in {inbox} — full pipeline coming soon.")


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
