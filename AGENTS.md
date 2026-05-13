# PaperClaw — agent guide

PaperClaw is a document-management CLI. It reads PDFs and other documents from
`~/inbox/`, classifies them, gives them sensible filenames, and moves them to
`~/library/` alongside a markdown transcript. A second command lets an agent
answer questions about the library. It is **not** a web service, a database
app, or a general-purpose file manager.

**Stack:** Python 3.14 (CPython via Homebrew), uv for packaging, ruff for
format + lint, mypy strict, pytest. HTTP calls via `httpx`; data shapes via
`pydantic`. No framework, no ORM.

## Non-obvious rules

- **Mutations must be idempotent.** Running the classify command twice on the
  same inbox must produce the same library — never duplicate files or create
  `_1` suffixes. Do: check the destination before writing.
- **Never silently swallow errors.** If a file can't be classified, log it at
  WARNING and skip it. Do not `except Exception: pass`.
- **All paths are `pathlib.Path`, never strings.** The ruff `PTH` rule enforces
  this, but write it that way from the start. Do: `Path(os.environ["..."])`.
- **Log to stdout only, never to a file.** Verbosity is controlled by
  `LOG_LEVEL`. Do not open a `FileHandler`.
- **`ANTHROPIC_API_KEY` comes from the environment, never from code.**
  Do not hardcode or default it. Fail fast with a clear message if it is unset.