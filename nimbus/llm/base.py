"""Interface comum para clientes LLM. Trocar provider = trocar arquivo."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any  # str (JSON) ou dict


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class ChatResponse:
    content: Optional[str]
    tool_calls: list[ToolCall]
    usage: Optional[Usage] = None
    raw: Any = None  # response original do provider, p/ debug


# Callback chamado para cada incremento de texto durante streaming.
# Quando passado em ``LLMClient.chat``, o cliente usa o modo streaming do
# provider e invoca este callback a cada delta de conteúdo recebido.
TextDeltaCallback = Callable[[str], None]


class LLMError(Exception):
    """Erro genérico de LLM (timeout, rate limit, etc.)."""


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float,
        on_text_delta: Optional[TextDeltaCallback] = None,
    ) -> ChatResponse: ...
