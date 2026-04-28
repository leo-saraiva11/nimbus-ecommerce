"""Garante que o modo debug imprime trace estruturado por turno."""
from __future__ import annotations
import json
from dataclasses import dataclass

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall, Usage


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
            _Hit(chunk=_Chunk(text="Direito de arrependimento em 7 dias.", source="politica_trocas.md"), score=0.812),
        ]


class _ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def chat(self, messages, tools, timeout, on_text_delta=None):
        return self._responses.pop(0)


def _make_agent(llm, rag=None, debug=True, data_dir=None, tmp_path=None):
    return Agent(
        llm=llm,
        rag=rag,
        config=AgentConfig(max_iterations=5, debug=debug),
        data_dir=data_dir,
        pedidos_dir=tmp_path,
        system_prompt_template="sis\n\n{rag_context}",
    )


def test_debug_off_nao_imprime_trace(data_dir, tmp_path, capsys):
    llm = _ScriptedLLM([ChatResponse(content="oi", tool_calls=[])])
    agent = _make_agent(llm, debug=False, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("oi")
    captured = capsys.readouterr().out
    assert "TURNO" not in captured


def test_debug_on_imprime_secoes_essenciais(data_dir, tmp_path, capsys):
    """Trace deve cobrir: turno, request/response do LLM, tool, final."""
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="search_products",
                                 arguments=json.dumps({"query": "logitech"}))],
        ),
        ChatResponse(content="Encontrei o Logitech G203.", tool_calls=[]),
    ])
    agent = _make_agent(llm, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("tem mouse logitech?")
    out = capsys.readouterr().out

    assert "TURNO #1" in out
    assert "Iteração 1" in out
    assert "Iteração 2" in out
    assert "LLM request" in out
    assert "LLM response" in out
    assert "TOOL search_products" in out
    assert "logitech" in out
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
    agent = _make_agent(llm, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("detalhes do P001")
    out = capsys.readouterr().out
    assert "Mouse Gamer Logitech G203" in out
    assert "descricao_curta" in out


def test_debug_on_mostra_tool_error(data_dir, tmp_path, capsys):
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="get_product",
                                 arguments=json.dumps({"produto_id": "P999"}))],
        ),
        ChatResponse(content="produto não existe", tool_calls=[]),
    ])
    agent = _make_agent(llm, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("detalhes do P999")
    out = capsys.readouterr().out
    assert "error" in out
    assert "P999" in out


def test_search_policies_eh_chamada_via_tool_quando_llm_decide(data_dir, tmp_path, capsys):
    """Comportamento novo: RAG NÃO é injetado automaticamente. O modelo chama search_policies."""
    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="search_policies",
                                 arguments=json.dumps({"query": "posso devolver?"}))],
        ),
        ChatResponse(content="Sim, em 7 dias (fonte: politica_trocas.md).", tool_calls=[]),
    ])
    agent = _make_agent(llm, rag=_StubRAG(), data_dir=data_dir, tmp_path=tmp_path)
    out = agent.run_turn("posso devolver um produto?")
    assert "7 dias" in out
    captured = capsys.readouterr().out
    assert "TOOL search_policies" in captured
    assert "politica_trocas.md" in captured
    assert "0.812" in captured


def test_debug_mostra_tokens_quando_disponiveis(data_dir, tmp_path, capsys):
    """Quando o provider devolve usage, o trace exibe prompt/completion/total + acumulado."""
    llm = _ScriptedLLM([
        ChatResponse(
            content="resposta direta",
            tool_calls=[],
            usage=Usage(prompt_tokens=120, completion_tokens=35, total_tokens=155),
        ),
    ])
    agent = _make_agent(llm, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("oi")
    out = capsys.readouterr().out
    assert "tokens prompt=120" in out
    assert "completion=35" in out
    assert "total=155" in out
    assert "Σ tokens neste turno" in out
    assert "Σ tokens acumulados" in out
    assert agent.total_usage.total_tokens == 155


def test_total_usage_acumula_entre_turnos(data_dir, tmp_path):
    llm = _ScriptedLLM([
        ChatResponse(content="t1", tool_calls=[], usage=Usage(10, 5, 15)),
        ChatResponse(content="t2", tool_calls=[], usage=Usage(20, 8, 28)),
    ])
    agent = _make_agent(llm, debug=False, data_dir=data_dir, tmp_path=tmp_path)
    agent.run_turn("primeiro")
    agent.run_turn("segundo")
    assert agent.total_usage.prompt_tokens == 30
    assert agent.total_usage.completion_tokens == 13
    assert agent.total_usage.total_tokens == 43
