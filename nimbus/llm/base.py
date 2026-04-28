"""Interface comum para clientes LLM. Trocar provider = trocar arquivo."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any  # str (JSON) ou dict


@dataclass
class ChatResponse:
    content: Optional[str]
    tool_calls: list[ToolCall]
    raw: Any = None  # response original do provider, p/ debug


class LLMError(Exception):
    """Erro genérico de LLM (timeout, rate limit, etc.)."""


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float,
    ) -> ChatResponse: ...
