"""Cliente Groq adaptado pra interface LLMClient."""
from __future__ import annotations
import os
from typing import Optional

from nimbus.llm.base import ChatResponse, LLMError, TextDeltaCallback, ToolCall, Usage
from nimbus.llm._stream_accumulator import accumulate_stream


class GroqClient:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from groq import Groq
        except ImportError as e:
            raise LLMError("Pacote `groq` não instalado") from e
        self.model = model or os.environ.get("NIMBUS_MODEL", "llama-3.3-70b-versatile")
        self._client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float,
        on_text_delta: Optional[TextDeltaCallback] = None,
    ) -> ChatResponse:
        if on_text_delta is not None:
            return self._chat_stream(messages, tools, timeout, on_text_delta)
        return self._chat_blocking(messages, tools, timeout)

    def _chat_blocking(self, messages, tools, timeout) -> ChatResponse:
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
        usage = None
        if getattr(resp, "usage", None):
            usage = Usage(
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
            )
        return ChatResponse(content=choice.content, tool_calls=tool_calls, usage=usage, raw=resp)

    def _chat_stream(self, messages, tools, timeout, on_text_delta) -> ChatResponse:
        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                timeout=timeout,
                stream=True,
                stream_options={"include_usage": True},
            )
        except Exception as e:
            raise LLMError(f"Erro na chamada Groq (stream): {e}") from e
        return accumulate_stream(stream, on_text_delta)
