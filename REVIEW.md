# Review Panel — What NOT to Flag

This file is read by the `mise run review` panel. Skip these known-intentional patterns.

## Intentional `type: ignore` comments
- `# type: ignore[typeddict-item]` in `anthropic_backend.py` — Anthropic SDK's `OutputConfigParam`
  TypedDict doesn't yet expose the `json_schema` format key; the workaround is correct.
- `# type: ignore[import-not-found]` on `pdf2image` / `pytesseract` — optional OCR deps that
  aren't installed in the default environment.

## Intentional `noqa` comments
- `# noqa: PLC0415` on lazy imports in `extract.py` and `store/index.py` — these modules load
  optional or heavy dependencies only when first used; top-level import would break non-OCR installs
  and slow startup.

## mypy overrides
- `disallow_any_explicit = false` for `paperclaw.ingest.classify` and `paperclaw.store.index` —
  required because pydantic's `BaseModel` and chromadb's collection API surface `Any` types that
  cannot be avoided without forking upstream stubs.

## Test helpers
- `cast(chromadb.Collection, object())` in `test_answer.py` — a deliberate fake; the collection is
  never called in the no-results path being tested.
- `FakeBackend` classes returning canned strings — intentional test doubles, not production code.

## Model string
- `"claude-sonnet-4-6"` in `anthropic_backend.py` is a model identifier, not a secret. Do not
  flag it as a hardcoded credential.

## Ruff / deptry suppressions
- `PLR2004`, `PLR0913` in the global ignore list — magic-value and arg-count rules disabled
  project-wide by agreement.
- `DEP002` ignore for `httpx` and `Pillow` — `httpx` is part of the stated stack for future HTTP
  calls; `Pillow` is a transitive dep of `pdf2image` (optional OCR extra).

## contextlib.suppress usage
- `contextlib.suppress(Exception)` around `client.delete_collection(...)` in `reindex` / `ingest`
  — Chroma raises if the collection doesn't exist yet; suppression is the documented pattern.

## load_dotenv at module level
- `load_dotenv()` at the top of `mcp_server.py` — intentional; the MCP server runs as a
  long-lived process and must pick up `.env` before any tool call.
