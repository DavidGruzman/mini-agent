import os
import time

import anthropic

DEFAULT_MODEL = os.environ.get("MINI_AGENT_MODEL", "claude-sonnet-5")
MAX_RETRIES = 3
MAX_TOKENS = 16000


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic(max_retries=0)
        self.model = model

    def send(self, system: str, messages: list[dict], tools: list[dict]):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    messages=messages,
                    tools=tools,
                )
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APITimeoutError, anthropic.InternalServerError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        raise last_error

    def list_models(self) -> list[str]:
        return [m.id for m in self.client.models.list()]
