"""Cliente Groq adaptado pra interface LLMClient."""
from __future__ import annotations
import os

from nimbus.llm.base import ChatResponse, LLMError, ToolCall


class GroqClient:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from groq import Groq
        except ImportError as e:
            raise LLMError("Pacote `groq` não instalado") from e
        self.model = model or os.environ.get("NIMBUS_MODEL", "llama-3.3-70b-versatile")
        self._client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatResponse:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                timeout=timeout,
            )
        except Exception as e:
            raise LLMError(f"Erro na chamada Groq: {e}") from e

        choice = resp.choices[0].message
        tool_calls = []
        for tc in (choice.tool_calls or []):
            tool_calls.append(ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=tc.function.arguments,
            ))
        return ChatResponse(
            content=choice.content,
            tool_calls=tool_calls,
            raw=resp,
        )
