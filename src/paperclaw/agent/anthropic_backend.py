import logging
import os

import anthropic
from dotenv import load_dotenv

log = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048


def _make_client() -> anthropic.Anthropic:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or export it in your shell before running paperclaw."
        )
    return anthropic.Anthropic(api_key=api_key)


class AnthropicBackend:
    def __init__(self) -> None:
        self._client = _make_client()

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        system_param: list[anthropic.types.TextBlockParam] = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        msg_list: list[anthropic.types.MessageParam] = [{"role": "user", "content": user}]

        if json_schema is not None:
            output_config: anthropic.types.OutputConfigParam = {
                "format": {
                    "type": "json_schema",
                    "schema": json_schema,
                }
            }
            response = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_param,
                messages=msg_list,
                output_config=output_config,
            )
        else:
            response = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_param,
                messages=msg_list,
            )

        block = response.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            raise RuntimeError(f"Unexpected content block type: {type(block).__name__!r}")
        return block.text
