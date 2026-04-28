"""Garante que o modo debug imprime trace estruturado por turno."""
from __future__ import annotations
import json
from dataclasses import dataclass

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


@dataclass
class _Hit:
    chunk: object
    score: float


@dataclass
class _Chunk:
    text: str
    source: str


class _StubRAG:
    def search(self, query, top_k=3):
        return [
            _Hit(chunk=_Chunk(text="política de devolução em 7 dias.", source="trocas.md"), score=0.812),
            _Hit(chunk=_Chunk(text="formas de pagamento aceitas.", source="pagamento.md"), score=0.671),
        ]


class _ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def chat(self, messages, tools, timeout):
        return self._responses.pop(0)


def test_debug_off_nao_imprime_trace(data_dir, tmp_path, capsys):
    llm = _ScriptedLLM([ChatResponse(content="oi", tool_calls=[])])
    agent = Agent(
        llm=llm, rag=_StubRAG(),
        config=AgentConfig(max_iterations=3, debug=False),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis\n\n{rag_context}",
    )
    agent.run_turn("oi")
    captured = capsys.readouterr().out
    assert "TURNO" not in captured
    assert "RAG retrieval" not in captured


def test_debug_on_imprime_secoes_essenciais(data_dir, tmp_path, capsys):
    """Trace deve cobrir: turno, RAG, request/response do LLM, tool, final."""
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="search_products",
                                 arguments=json.dumps({"query": "logitech"}))],
        ),
        ChatResponse(content="Encontrei o Logitech G203.", tool_calls=[]),
    ])
    agent = Agent(
        llm=llm, rag=_StubRAG(),
        config=AgentConfig(max_iterations=5, debug=True),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis\n\n{rag_context}",
    )
    agent.run_turn("tem mouse logitech?")
    out = capsys.readouterr().out

    # cabeçalho de turno
    assert "TURNO #1" in out
    # bloco RAG com score e fonte
    assert "RAG retrieval" in out
    assert "trocas.md" in out
    assert "0.812" in out
    # iterações do loop
    assert "Iteração 1" in out
    assert "Iteração 2" in out
    # request + response do LLM
    assert "LLM request" in out
    assert "LLM response" in out
    # tool com nome, args e result
    assert "TOOL search_products" in out
    assert "logitech" in out
    # resposta final
    assert "FINAL" in out
    assert "Logitech G203" in out


def test_debug_on_mostra_resultado_completo_da_tool(data_dir, tmp_path, capsys):
    """Modo debug não trunca o output da tool."""
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="get_product",
                                 arguments=json.dumps({"produto_id": "P001"}))],
        ),
        ChatResponse(content="ok", tool_calls=[]),
    ])
    agent = Agent(
        llm=llm, rag=_StubRAG(),
        config=AgentConfig(debug=True),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis\n\n{rag_context}",
    )
    agent.run_turn("detalhes do P001")
    out = capsys.readouterr().out
    # o resultado completo da tool (com descrição_curta etc.) deve estar no trace
    assert "Mouse Gamer Logitech G203" in out
    assert "descricao_curta" in out  # campo do CSV no JSON


def test_debug_on_mostra_tool_error(data_dir, tmp_path, capsys):
    """Erro de tool aparece no trace e o status reflete 'error'."""
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="get_product",
                                 arguments=json.dumps({"produto_id": "P999"}))],
        ),
        ChatResponse(content="produto não existe", tool_calls=[]),
    ])
    agent = Agent(
        llm=llm, rag=_StubRAG(),
        config=AgentConfig(debug=True),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis\n\n{rag_context}",
    )
    agent.run_turn("detalhes do P999")
    out = capsys.readouterr().out
    assert "error" in out
    assert "P999" in out
