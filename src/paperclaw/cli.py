import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from paperclaw.agent.anthropic_backend import AnthropicBackend
from paperclaw.ingest.pipeline import run

app = typer.Typer(name="paperclaw", no_args_is_help=True, add_completion=False)
log = logging.getLogger(__name__)

_DEFAULT_INBOX = "~/inbox"
_DEFAULT_LIBRARY = "~/library"


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
    inbox_path = inbox or Path(os.environ.get("PAPERCLAW_INBOX", _DEFAULT_INBOX)).expanduser()
    library_path = (
        library or Path(os.environ.get("PAPERCLAW_LIBRARY", _DEFAULT_LIBRARY)).expanduser()
    )

    if not inbox_path.is_dir():
        typer.echo(f"error: inbox {inbox_path} is not a directory", err=True)
        raise typer.Exit(2)

    try:
        backend = AnthropicBackend()
    except RuntimeError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    result = run(inbox_path, library_path, backend)

    typer.echo(
        f"Done: {result.total} PDF(s) found, "
        f"{result.added} added, {result.skipped} skipped, {result.failed} failed."
    )
    if result.failed:
        raise typer.Exit(4)


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
