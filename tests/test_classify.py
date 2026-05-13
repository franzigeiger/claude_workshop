import json

from paperclaw.ingest.classify import Classification, _extract_json, classify


class FakeBackend:
    def __init__(self, payload: dict[str, object], *, wrap_in_fences: bool = False) -> None:
        self._payload = payload
        self._wrap = wrap_in_fences

    def chat(self, system: str, user: str, **_: object) -> str:
        raw = json.dumps(self._payload)
        return f"```json\n{raw}\n```" if self._wrap else raw


def _invoice_payload() -> dict[str, object]:
    return {
        "kind": "invoice",
        "topic": "utility",
        "doc_date": "2024-11-03",
        "issuer": "Stadtwerke München",
        "short_desc": "strom-q3",
        "summary": "Electricity invoice for Q3 2024 from Stadtwerke München.",
        "confidence": 0.95,
        "notes": "",
    }


def test_classify_returns_classification() -> None:
    result = classify("invoice text here", FakeBackend(_invoice_payload()))
    assert isinstance(result, Classification)


def test_classify_parses_kind_and_topic() -> None:
    result = classify("invoice text here", FakeBackend(_invoice_payload()))
    assert result.kind == "invoice"
    assert result.topic == "utility"


def test_classify_parses_confidence() -> None:
    result = classify("invoice text here", FakeBackend(_invoice_payload()))
    assert result.confidence == 0.95


def test_classify_null_topic() -> None:
    payload = _invoice_payload()
    payload["topic"] = None
    result = classify("letter text", FakeBackend(payload))
    assert result.topic is None


def test_classify_null_date() -> None:
    payload = _invoice_payload()
    payload["doc_date"] = None
    result = classify("undated doc", FakeBackend(payload))
    assert result.doc_date is None


def test_classify_low_confidence_still_returns() -> None:
    payload = _invoice_payload()
    payload["confidence"] = 0.35
    result = classify("ambiguous text", FakeBackend(payload))
    assert result.confidence < 0.6


def test_classify_strips_markdown_fences() -> None:
    result = classify("invoice text", FakeBackend(_invoice_payload(), wrap_in_fences=True))
    assert result.kind == "invoice"


def test_extract_json_plain() -> None:
    assert _extract_json('{"a": 1}') == '{"a": 1}'


def test_extract_json_strips_json_fence() -> None:
    assert _extract_json("```json\n{}\n```") == "{}"


def test_extract_json_strips_plain_fence() -> None:
    assert _extract_json("```\n{}\n```") == "{}"
