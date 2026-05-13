# PaperClaw — Design

Living architecture document. Update whenever a significant decision is made or changed. See `project.md` for the product brief and `context.md` for the working agreement.

## 1. Goals & non-goals

**Goals**
- Turn `~/inbox/` of PDFs into a searchable `~/library/` with consistent filenames and a markdown transcript next to each PDF.
- A CLI agent that answers natural-language questions over the library ("invoice for that gadget from three months ago", "all Finanzamt letters from 2024").
- Private-by-default capable: the full pipeline must be runnable without any external API call.

**Non-goals (for the 3-hour workshop scope)**
- Web UI, multi-user access, document editing, fine-tuning local models.
- Long-term incremental ingestion daemons / file watchers (one-shot ingest is enough).
- Migration / schema-evolution tooling for the vector store.

## 2. Pipeline

```
~/inbox/*.pdf
   │
   ▼  extract (pypdf/pdfplumber → fallback: tesseract DE+EN)
text + page metadata
   │
   ▼  classify (LLM backend: Anthropic ⇄ Ollama)
{category, doc_date, issuer, short_desc, summary}
   │
   ▼  rename + transcribe
~/library/<kind-plural>/<year>/<stem>.pdf  +  .md
   │
   ▼  embed (sentence-transformers, multilingual)
Chroma vector store with metadata
   │
   ▼  ask (retrieve top-k → answer via LLM backend)
answer + cited source paths
```

`<stem>` = `YYYY-MM-DD__<category>__<issuer-slug>__<short-desc>` (double underscore as field separator; slug uses single hyphens). Date and category live in filenames **and** in vector-store metadata; the metadata is the source of truth, the filename is for humans.

## 3. Components

| Module | Responsibility |
|---|---|
| `paperclaw.ingest.extract` | PDF → plain text. Try text layer first; if empty/garbage, OCR with tesseract. |
| `paperclaw.ingest.classify` | Plain text → `Classification` dataclass via LLM backend. Fixed category enum. |
| `paperclaw.ingest.pipeline` | Orchestrates extract → classify → write → index for a folder. |
| `paperclaw.store.library` | Writes the renamed PDF and the `.md` transcript to `~/library/`. |
| `paperclaw.store.index` | Embeds transcripts and writes to Chroma; query API for the agent. |
| `paperclaw.agent.backend` | `LLMBackend` Protocol with `chat()` method. Two implementations. |
| `paperclaw.agent.anthropic_backend` | Calls Claude (Sonnet 4.6 default). |
| `paperclaw.agent.ollama_backend` | Calls a local Ollama server. |
| `paperclaw.agent.answer` | RAG loop: embed query → top-k → prompt template → backend → answer. |
| `paperclaw.cli` | `paperclaw ingest`, `paperclaw ask`, `paperclaw reindex`. |

## 4. Storage layout

```
~/inbox/                              # user-controlled, never written to by paperclaw
~/library/
  invoices/
    2024/
      2024-11-03__invoice__stadtwerke-muenchen__strom-q3.pdf
      2024-11-03__invoice__stadtwerke-muenchen__strom-q3.md
    unknown-year/
  statements/
    2024/
  letters/
    2025/
  contracts/  receipts/  notices/  other/
~/.paperclaw/
  chroma/                             # local vector store (sqlite-backed)
  cache/                              # extracted text + embeddings, keyed by PDF SHA-256
  config.toml                         # backend, model names, paths
  logs/
```

The library is bucketed `~/library/<kind-plural>/<year>/`, with `unknown-year/` for documents whose date the classifier cannot determine. `topic` is intentionally **not** in the path — a doc with two facets cannot live in two folders at once, so cross-tagging stays in metadata.

All structured metadata still lives in Chroma alongside each embedding (`kind`, `topic`, `doc_date`, `issuer`, `short_desc`, `confidence`, `notes`, `taxonomy_version`, `source_pdf`, `source_md`). The folder layout is for humans browsing the library; the agent and `paperclaw list` query Chroma. Reclassifying a document is now a folder move + filename refresh, not just a metadata edit — the `reclassify` command performs both atomically.

## 5. LLM backend abstraction

One Protocol, two implementations, selected by `PAPERCLAW_BACKEND` env var (`anthropic` | `ollama`, default `anthropic` for the workshop).

```python
class LLMBackend(Protocol):
    def chat(self, system: str, user: str, *, json_schema: dict | None = None) -> str: ...
```

- `json_schema` is honoured by the Anthropic backend via tool-use / structured output. For Ollama, we use the `format: json` flag and validate manually.
- Embedding is **not** behind this protocol. Both backends share a single local embedding model (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) so the Chroma index is reproducible regardless of which chat backend you used during ingest.

## 6. Taxonomy

Two-tier per document: required `kind` × optional `topic`.

- `kind` is what the document **is**: `invoice`, `statement`, `letter`, `contract`, `receipt`, `notice`, `other`.
- `topic` is what it **concerns**: `utility`, `bank`, `insurance`, `tax`, `employer`, `health`, `government`, `private`, or `null`.

The vocabulary lives in `categories.yaml` at the repo root, loaded at startup. It is the single source of truth: the classifier prompt is generated from it, and the Chroma metadata schema validates against it. Adding a value is a YAML edit plus a `taxonomy_version` bump — no Python change, no rebuild.

The classifier returns `{kind, topic, confidence, notes}`. If `confidence < 0.6`, the document is still ingested but flagged for `paperclaw review` rather than silently filed. Confidence and notes are stored as Chroma metadata so bulk-corrections later are cheap.

Each ingested document carries `taxonomy_version` in its metadata. Editing `categories.yaml` increments the version; `paperclaw reclassify --stale` re-runs only the docs whose stored version is older than the current one. OCR output and embeddings live in `~/.paperclaw/cache/` keyed by content SHA-256, so re-classification skips the expensive steps.

## 7. Tooling decisions

| Concern | Choice | Why |
|---|---|---|
| Package manager | `uv` | Fast, lockfile-first, plays well with Python 3.14. |
| Lint + format | `ruff` | One tool, fast, replaces flake8/black/isort. |
| Type checking | `mypy --strict` | Workshop requires strong typing everywhere. |
| Pre-commit | `pre-commit` w/ ruff + mypy + `detect-secrets` | Enforces the "no API keys committed" basic. |
| Tests | `pytest` | Standard. Fixtures committed under `tests/fixtures/pdfs/` are synthetic only. |
| PDF text | `pypdf` (primary) + `pdfplumber` (tables) | Pure Python, no system deps for born-digital PDFs. |
| OCR | system `tesseract` + `pytesseract`, DE+EN | Free, local, multilingual. |
| Embeddings | `sentence-transformers` multilingual MiniLM | Small, CPU-friendly, DE+EN. |
| Vector store | `chromadb` (sqlite persistence) | Single file, no server, metadata filters. |
| Chat LLM (API) | Anthropic `claude-sonnet-4-6` | Latest Sonnet, good DE handling, JSON tool-use. |
| Chat LLM (local) | Ollama with `qwen2.5:7b-instruct` (default) | Better DE than llama3 7B at similar cost. |
| CLI | `typer` | Cheap to get nice help / typed args in 3 h. |
| Progress + resilience | `tqdm` + per-doc `try/except`, batched embedding (32–64) | Sized for the 100–1000 doc demo target; one bad PDF never kills the run. |
| Config / secrets | `python-dotenv` + `~/.paperclaw/config.toml` | `.env` for `ANTHROPIC_API_KEY`, never committed. |
| Synthetic PDFs | `reportlab` | Lets us craft DE/EN invoice + Finanzamt-style fixtures. |

## 8. Repository layout

```
paperclaw/                   # source package
  ingest/  store/  agent/  cli.py
tests/
  fixtures/pdfs/             # synthetic, committed
  test_extract.py  test_classify.py  test_index.py  test_agent.py
scripts/
  make_synthetic_pdfs.py
content/
  project.md  context.md  design.md
pyproject.toml
.pre-commit-config.yaml
.env.example
README.md
```

## 9. Testing strategy

- Unit: `extract`, `rename` (filename builder is deterministic and pure), classifier prompt parsing, index round-trip.
- Integration: end-to-end on the synthetic fixture set — ingest a folder, query Chroma, ask a few canned questions, assert citations land on the expected files.
- The LLM backends are mocked in unit tests via a `FakeBackend` returning canned strings/JSON. Integration tests run against the real Ollama backend in CI-equivalent local runs; the Anthropic backend is exercised by an opt-in smoke test gated on `ANTHROPIC_API_KEY`.

## 10. Decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-13 | Hybrid LLM backend (Anthropic API + Ollama) behind one Protocol | Get workshop-quality demo via API while keeping the private-by-default path real and tested. |
| 2026-05-13 | Text-layer first, tesseract fallback (DE+EN) | Cheapest fast path for born-digital PDFs; OCR only when needed. |
| 2026-05-13 | Vector RAG only (no separate manifest) | Chroma metadata covers structured filters; one store = less to maintain in 3 h. |
| 2026-05-13 | CLI-only interface | Smallest demoable surface that fits the time budget. |
| 2026-05-13 | Synthetic PDFs committed; real PDFs only on local disk | Reproducible tests without exposing personal paperwork. |
| 2026-05-13 | Embeddings shared across backends (local sentence-transformers) | Keeps Chroma reproducible regardless of which chat backend was used during ingest. |
| 2026-05-13 | ~~Flat `~/library/` with metadata in Chroma, not a folder-per-category tree~~ | ~~Search-driven UX doesn't need browsable folders; renaming on re-classify becomes trivial.~~ Superseded — see next row. |
| 2026-05-13 | Library bucketed by `kind`/`year`: `~/library/<kind-plural>/<year>/` | Humans want to browse "all 2024 invoices" without spinning up the agent. `topic` stays in metadata only since cross-tagging can't render in a tree. |
| 2026-05-13 | Two-tier taxonomy: required `kind` × optional `topic` | Cleanly answers both "all invoices from 2024" and "all Finanzamt correspondence" without label conflation. |
| 2026-05-13 | `categories.yaml` at repo root as single source of truth for taxonomy | Editing taxonomy is editing one file; classifier prompt and metadata schema regenerate from it. No code change to add a category. |
| 2026-05-13 | `taxonomy_version` in every doc's metadata; content-hashed cache in `~/.paperclaw/cache/` | Re-classification after a taxonomy edit only re-runs the classifier; OCR and embeddings are reused. Avoids the "I added one category, must rerun everything" footgun. |

## 11. CLI surface

The CLI is the single human and agent interface. Two non-negotiable design rules so an LLM agent can drive it reliably:

- **Machine-parseable on demand.** Every command supports `--format json`. JSON goes to **stdout**; logs and progress bars go to **stderr**. Piping `paperclaw … --format json | jq …` always works.
- **Stable exit codes.** `0` success · `1` unexpected/internal error · `2` user error (bad flags, missing path) · `3` nothing to do (already ingested, no matches) · `4` partial success with documents flagged for review.

### Commands

| Command | Purpose | Notable flags |
|---|---|---|
| `paperclaw ingest <inbox_path>` | Run the full pipeline on a folder of PDFs. Idempotent — re-ingesting a folder is a no-op for already-processed content (keyed by SHA-256). | `--dry-run` shows the plan without writing. `--no-classify` extracts + indexes only. |
| `paperclaw ask "<question>"` | RAG answer over the library. Returns answer + cited source paths. | `--k 5` top-k retrieval. `--kind invoice --topic utility --year 2024` pre-filters retrieval by metadata. |
| `paperclaw list` | Query the library by structured metadata. Stream-friendly. | `--kind`, `--topic`, `--year`, `--issuer`, `--needs-review`, `--limit`. |
| `paperclaw show <doc_id\|path>` | Full metadata + path to transcript for one document. | `--with-transcript` inlines the markdown body. |
| `paperclaw review` | Lists docs flagged with `confidence < 0.6`. | `--apply <doc_id> --kind X --topic Y` accepts a manual correction. |
| `paperclaw reclassify` | Re-run classifier on selected docs. Moves + renames atomically. | `--stale` (taxonomy_version older than current), `--doc <id>`, `--kind invoice`, `--yes`. |
| `paperclaw reindex` | Rebuild Chroma from `~/library/*.md`. Safe after manual edits. | `--from-scratch` drops and rebuilds. |
| `paperclaw config` | Print resolved config (backend, models, paths). Read-only. | `--format json` recommended for agents. |
| `paperclaw doctor` | Environment health check: tesseract installed, Ollama reachable if `PAPERCLAW_BACKEND=ollama`, `ANTHROPIC_API_KEY` set if `=anthropic`, cache + library writable. | Exit code `0` healthy, `1` issues. |

### Common flags

`--format {text,json}` (default `text`) · `--quiet` / `-q` · `--verbose` / `-v` (repeatable) · `--backend {anthropic,ollama}` (one-shot override of env var) · `--yes` (auto-confirm destructive ops). No command prompts interactively when stdin isn't a TTY — it fails with exit `2` instead. This keeps agent invocations deterministic.

### JSON envelope

All `--format json` output uses one stable envelope so an agent can branch on `ok` and ignore the rest:

```json
{
  "ok": true,
  "command": "ingest",
  "version": 1,
  "data": { "processed": 12, "added": 10, "skipped_duplicate": 2, "needs_review": 1,
            "documents": [ { "sha256": "...", "kind": "invoice", "topic": "utility",
                              "doc_date": "2024-11-03", "library_path": "invoices/2024/...",
                              "confidence": 0.92, "needs_review": false } ] },
  "warnings": []
}
```

On failure: `{"ok": false, "command": "...", "version": 1, "error": {"code": "BAD_PATH", "message": "..."}}` with the corresponding non-zero exit code. Error `code`s are an additive enum documented in the `--help` for each command.

## 12. Open questions

None currently outstanding — see decisions log §10.
