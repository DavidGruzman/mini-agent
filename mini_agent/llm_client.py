import os

import anthropic

DEFAULT_MODEL = os.environ.get("MINI_AGENT_MODEL", "claude-sonnet-5")
MAX_TOKENS = 16000


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic()
        self.model = model

    def send(self, system: str, messages: list[dict], tools: list[dict]):
        return self.client.messages.create(
            model=self.model, max_tokens=MAX_TOKENS, system=system, messages=messages, tools=tools
        )

    def list_models(self) -> list[str]:
        return [m.id for m in self.client.models.list()]
