from typing import Protocol


class LLMBackend(Protocol):
    def chat(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, object] | None = None,
    ) -> str: ...
