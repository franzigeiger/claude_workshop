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

## Hooks and guardrails

- **docs-drift (pre-commit):** fires when `src/**/*.py` is staged. Warns if neither
  `content/design.md` nor `content/project.md` is also staged. It checks with
  `git diff --cached --name-only | grep -qE '^content/(design|project)\.md$'` — update
  a doc file to silence it.
- **danger (pre-push):** blocks pushes that touch `src/paperclaw/store/**` or
  `categories.yaml` unless `PAPERCLAW_DANGER_OK=1` is set. Work through the printed
  checklist before setting that flag.
- **review panel:** `mise run review` runs three specialist Claude agents (security,
  correctness, architecture) over the current branch diff. Run it before opening a PR.
  See `REVIEW.md` for the list of intentional patterns reviewers should skip.