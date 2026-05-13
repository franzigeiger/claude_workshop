# PaperClaw

Turn a folder of everyday paperwork into an organized, searchable document library.

PDFs go in `~/inbox/`, get classified and renamed, and land in `~/library/` next to a markdown transcript. A CLI agent can then answer questions like "find the invoice for that gadget from three months ago."

## Quick start

```sh
# 1. Install toolchain (requires mise and uv)
mise install
mise run setup

# 2. Run all checks
mise run check

# 3. Run the CLI
uv run paperclaw
```

## Development

| Command | What it does |
|---------|-------------|
| `mise run setup` | Install deps, copy `.env.example` → `.env`, install git hooks |
| `mise run check` | Format check + lint + type check + tests (all must be clean) |
| `mise run fmt` | Auto-format all Python files |
| `uv run pytest` | Run tests only |

## Configuration

Copy `.env.example` to `.env` and set:

- `ANTHROPIC_API_KEY` — required for classification and Q&A
- `PAPERCLAW_INBOX` — source folder (default: `~/inbox`)
- `PAPERCLAW_LIBRARY` — destination folder (default: `~/Documents/paperclaw-library`)
- `LOG_LEVEL` — verbosity: `DEBUG | INFO | WARNING | ERROR`