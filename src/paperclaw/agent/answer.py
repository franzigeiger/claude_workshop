"""RAG-based question answering over the PaperClaw library."""

import logging
from dataclasses import dataclass

import chromadb

from paperclaw.agent.backend import LLMBackend
from paperclaw.store.index import EmbedFn, SearchResult, query

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a helpful assistant that answers questions about a personal document library. "
    "Use only the provided document excerpts to answer. "
    "Cite the document IDs you relied on. "
    "If the answer cannot be found in the documents, say so clearly."
)


@dataclass
class AnswerResult:
    answer: str
    sources: list[str]


def _build_context(results: list[SearchResult]) -> str:
    parts: list[str] = []
    for r in results:
        meta = r.metadata
        header = (
            f"[{r.doc_id}]"
            f" {meta.get('kind', 'document')}"
            f" | {meta.get('issuer', 'unknown issuer')}"
            f" | {meta.get('doc_date', 'n/a')}"
        )
        parts.append(f"{header}\n{r.text[:800]}")
    return "\n\n---\n\n".join(parts)


def answer(
    question: str,
    collection: chromadb.Collection,
    backend: LLMBackend,
    embed_fn: EmbedFn,
    *,
    k: int = 5,
    filters: dict[str, str] | None = None,
) -> AnswerResult:
    """Retrieve top-k documents then answer the question via the LLM backend."""
    results = query(collection, question, k, filters=filters, embed_fn=embed_fn)

    if not results:
        return AnswerResult(
            answer="No relevant documents found in the library.",
            sources=[],
        )

    user = f"Question: {question}\n\nDocument excerpts:\n\n{_build_context(results)}"
    answer_text = backend.chat(_SYSTEM, user)
    return AnswerResult(
        answer=answer_text,
        sources=[r.doc_id for r in results],
    )
