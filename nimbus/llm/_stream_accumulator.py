"""Acumula chunks de streaming OpenAI-compatible em uma ChatResponse final.

Tanto o SDK ``groq`` quanto ``openai`` (usado para OpenRouter) emitem deltas
no mesmo formato — esta função funciona para ambos. Cada chunk traz um
``choices[0].delta`` que pode conter ``content`` (string) e/ou ``tool_calls``
(lista parcial). Tool calls vêm fragmentados: um chunk traz ``index`` + ``id``
+ ``function.name`` (no início) e os subsequentes trazem o mesmo ``index``
com mais pedaços do ``function.arguments`` (JSON sendo construído char a
char). Reconstruímos por ``index``.

A última mensagem (após ``finish_reason``) traz ``usage`` quando o request foi
feito com ``stream_options={"include_usage": True}``.
"""
from __future__ import annotations
from typing import Iterable

from nimbus.llm.base import ChatResponse, TextDeltaCallback, ToolCall, Usage


def accumulate_stream(stream: Iterable, on_text_delta: TextDeltaCallback) -> ChatResponse:
    content_parts: list[str] = []
    tc_acc: dict[int, dict] = {}  # index -> {id, name, arguments_str}
    usage: Usage | None = None

    for chunk in stream:
        if getattr(chunk, "choices", None):
            choice = chunk.choices[0]
            delta = choice.delta

            # texto
            content = getattr(delta, "content", None)
            if content:
                content_parts.append(content)
                on_text_delta(content)

            # tool calls — chegam parcelados por index
            for tc in (getattr(delta, "tool_calls", None) or []):
                idx = tc.index
                if idx not in tc_acc:
                    tc_acc[idx] = {"id": "", "name": "", "arguments": ""}
                if tc.id:
                    tc_acc[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tc_acc[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        tc_acc[idx]["arguments"] += tc.function.arguments

        # usage só vem no chunk final (com include_usage=True)
        u = getattr(chunk, "usage", None)
        if u:
            usage = Usage(
                prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(u, "completion_tokens", 0) or 0,
                total_tokens=getattr(u, "total_tokens", 0) or 0,
            )

    tool_calls = [
        ToolCall(id=v["id"], name=v["name"], arguments=v["arguments"])
        for _, v in sorted(tc_acc.items())
    ]
    content = "".join(content_parts) if content_parts else None
    return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
