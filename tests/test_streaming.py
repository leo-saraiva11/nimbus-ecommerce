"""Streaming de resposta: agent.run_turn invoca on_text_delta com cada
fragmento de texto, e o conteúdo final é o concatenado dos fragmentos."""
from __future__ import annotations
import json

from nimbus.agent import Agent, AgentConfig
from nimbus.llm._stream_accumulator import accumulate_stream
from nimbus.llm.base import ChatResponse, ToolCall, Usage


class _StreamingLLM:
    """Mock que simula um provider streaming: quando on_text_delta é passado,
    chama o callback com cada delta antes de devolver o ChatResponse final."""

    def __init__(self, scripted_responses):
        # cada item: (deltas: list[str] | None, ChatResponse final)
        self._items = list(scripted_responses)

    def chat(self, messages, tools, timeout, on_text_delta=None):
        deltas, final = self._items.pop(0)
        if on_text_delta and deltas:
            for d in deltas:
                on_text_delta(d)
        return final


def _make(llm, data_dir, tmp_path, stream=True, debug=False):
    return Agent(
        llm=llm, rag=None,
        config=AgentConfig(stream=stream, debug=debug),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis",
    )


def test_stream_invoca_callback_com_cada_delta(data_dir, tmp_path):
    captured = []
    deltas = ["Olá", " ", "tudo", " bem", "?"]
    llm = _StreamingLLM([(deltas, ChatResponse(content="Olá tudo bem?", tool_calls=[]))])
    agent = _make(llm, data_dir, tmp_path, stream=True)
    agent.run_turn("oi", on_text_delta=captured.append)
    assert captured == deltas
    assert "".join(captured) == "Olá tudo bem?"


def test_stream_desligado_ignora_callback(data_dir, tmp_path):
    """Quando AgentConfig.stream=False, o callback nunca é invocado."""
    captured = []
    deltas = ["nao", " deveria", " aparecer"]
    llm = _StreamingLLM([(deltas, ChatResponse(content="ok", tool_calls=[]))])
    agent = _make(llm, data_dir, tmp_path, stream=False)
    agent.run_turn("oi", on_text_delta=captured.append)
    assert captured == []


def test_stream_atravessa_iteracoes_de_tool_call(data_dir, tmp_path):
    """Stream funciona em loop multi-iteração (texto só aparece no final)."""
    captured = []
    deltas_finais = ["Encontrei", " o produto."]
    llm = _StreamingLLM([
        # iteração 1: tool call, sem texto
        (None, ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="get_product",
                                 arguments=json.dumps({"produto_id": "P001"}))],
        )),
        # iteração 2: texto final streamado
        (deltas_finais, ChatResponse(content="Encontrei o produto.", tool_calls=[])),
    ])
    agent = _make(llm, data_dir, tmp_path, stream=True)
    agent.run_turn("detalhes do P001", on_text_delta=captured.append)
    assert "".join(captured) == "Encontrei o produto."


# --- accumulator -----------------------------------------------------------

class _FakeChunk:
    """Mimica chunk.choices[0].delta com optional content e tool_calls."""

    class _Choice:
        def __init__(self, delta):
            self.delta = delta

    def __init__(self, content=None, tc_chunks=None, usage=None):
        class _Delta:
            pass
        d = _Delta()
        d.content = content
        d.tool_calls = tc_chunks
        self.choices = [self._Choice(d)]
        self.usage = usage


class _FakeTC:
    def __init__(self, index, id_=None, name=None, arguments=None):
        self.index = index
        self.id = id_

        class _Fn:
            pass
        fn = _Fn()
        fn.name = name
        fn.arguments = arguments
        self.function = fn


class _FakeUsage:
    def __init__(self, p, c, t):
        self.prompt_tokens = p
        self.completion_tokens = c
        self.total_tokens = t


def test_accumulator_concatena_text_deltas():
    captured = []
    chunks = [
        _FakeChunk(content="Olá"),
        _FakeChunk(content=", "),
        _FakeChunk(content="mundo!"),
        _FakeChunk(usage=_FakeUsage(10, 5, 15)),
    ]
    resp = accumulate_stream(chunks, captured.append)
    assert resp.content == "Olá, mundo!"
    assert captured == ["Olá", ", ", "mundo!"]
    assert resp.usage == Usage(10, 5, 15)


def test_accumulator_reconstroi_tool_calls_fragmentadas():
    """Tool calls vêm em chunks com index igual e arguments parciais."""
    captured = []
    chunks = [
        _FakeChunk(tc_chunks=[_FakeTC(0, id_="call_1", name="get_product")]),
        _FakeChunk(tc_chunks=[_FakeTC(0, arguments='{"produto')]),
        _FakeChunk(tc_chunks=[_FakeTC(0, arguments='_id":"P001"}')]),
    ]
    resp = accumulate_stream(chunks, captured.append)
    assert resp.content is None
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert tc.id == "call_1"
    assert tc.name == "get_product"
    assert tc.arguments == '{"produto_id":"P001"}'
