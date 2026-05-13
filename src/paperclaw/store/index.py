"""Chroma-backed vector index for the PaperClaw library."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import chromadb
import chromadb.api

log = logging.getLogger(__name__)

EmbedFn = Callable[[list[str]], list[list[float]]]
_COLLECTION_NAME = "paperclaw"


@lru_cache(maxsize=1)
def _load_model() -> Any:
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is not installed. Run: uv sync") from exc
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def default_embed(texts: list[str]) -> list[list[float]]:
    """Embed texts with the local multilingual MiniLM model."""
    model = _load_model()
    return cast(list[list[float]], model.encode(texts, convert_to_numpy=True).tolist())


@dataclass
class SearchResult:
    doc_id: str
    text: str
    distance: float
    metadata: dict[str, str | int | float | bool]


def get_client(chroma_path: Path) -> chromadb.api.ClientAPI:
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def get_collection(client: chromadb.api.ClientAPI) -> chromadb.Collection:
    return client.get_or_create_collection(_COLLECTION_NAME)


def add_document(
    collection: chromadb.Collection,
    doc_id: str,
    text: str,
    metadata: dict[str, str | int | float | bool],
    embed_fn: EmbedFn,
) -> None:
    vec: Sequence[float] = embed_fn([text])[0]
    collection.upsert(
        ids=[doc_id],
        embeddings=[vec],
        documents=[text],
        metadatas=[metadata],
    )
    log.debug("Indexed %s", doc_id)


def query(
    collection: chromadb.Collection,
    question: str,
    k: int,
    filters: dict[str, str] | None,
    embed_fn: EmbedFn,
) -> list[SearchResult]:
    vec: Sequence[float] = embed_fn([question])[0]
    where: dict[str, Any] | None = dict(filters) if filters else None
    raw = collection.query(
        query_embeddings=[vec],
        n_results=k,
        where=where,
    )
    ids: list[str] = (raw["ids"] or [[]])[0]
    docs: list[str] = ((raw["documents"] or [[]])[0]) or []
    dists: list[float] = ((raw["distances"] or [[]])[0]) or []
    metas: list[Any] = ((raw["metadatas"] or [[]])[0]) or []

    return [
        SearchResult(
            doc_id=doc_id,
            text=doc_text,
            distance=dist,
            metadata=cast(dict[str, str | int | float | bool], meta),
        )
        for doc_id, doc_text, dist, meta in zip(ids, docs, dists, metas, strict=True)
    ]
