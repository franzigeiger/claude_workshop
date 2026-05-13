import importlib.resources
import json
import logging
import re
from functools import lru_cache
from typing import TypedDict, cast

import yaml
from pydantic import BaseModel

from paperclaw.agent.backend import LLMBackend

log = logging.getLogger(__name__)


class Taxonomy(TypedDict):
    version: int
    kinds: dict[str, str]
    topics: list[str]


class Classification(BaseModel):
    kind: str
    topic: str | None
    doc_date: str | None
    issuer: str | None
    short_desc: str | None
    summary: str
    confidence: float
    notes: str


@lru_cache(maxsize=1)
def load_taxonomy() -> Taxonomy:
    pkg = importlib.resources.files("paperclaw")
    text = (pkg / "categories.yaml").read_text(encoding="utf-8")
    return cast(Taxonomy, yaml.safe_load(text))


@lru_cache(maxsize=1)
def _build_system_prompt() -> str:
    tax = load_taxonomy()
    kinds = ", ".join(tax["kinds"])
    topics = ", ".join(tax["topics"])
    return (
        "You are a document classifier. Analyse the document text and return ONLY a raw JSON object"
        " — no markdown, no code fences, no explanation.\n\n"
        f"Allowed `kind` values: {kinds}\n"
        f"Allowed `topic` values: {topics} (or null)\n\n"
        "Rules:\n"
        "- `kind` must be exactly one of the allowed values.\n"
        "- `topic` must be exactly one of the allowed values, or null.\n"
        "- `doc_date` is the document's own date in ISO 8601 (YYYY-MM-DD), or null.\n"
        "- `issuer` is the company or authority that issued the document, or null.\n"
        "- `short_desc` is a brief slug-friendly label (≤ 40 chars, lowercase, hyphens ok).\n"
        "- `summary` is a 1-2 sentence human-readable description.\n"
        "- `confidence` is your confidence in the classification (0.0-1.0).\n"
        "- `notes` explains any uncertainty (empty string is fine when confident)."
    )


def _extract_json(raw: str) -> str:
    """Strip markdown code fences if present, then return the JSON string."""
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
    return stripped.strip()


def classify(text: str, backend: LLMBackend) -> Classification:
    """Classify a document's plain text via the given LLM backend."""
    system = _build_system_prompt()
    raw = backend.chat(system, text)
    return Classification.model_validate(json.loads(_extract_json(raw)))
