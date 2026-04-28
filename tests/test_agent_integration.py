import json
import pytest
from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


class ScriptedLLM:
    """LLM mockado: percorre lista de respostas pré-definidas."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.received_messages = []

    def chat(self, messages, tools, timeout, on_text_delta=None):
        self.received_messages.append(messages)
        return self._responses.pop(0)


def test_agente_executa_tool_e_finaliza(data_dir, tmp_path):
    llm = ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="search_products",
                                 arguments=json.dumps({"query": "logitech"}))],
        ),
        ChatResponse(
            content="Encontrei o Mouse Logitech G203 (P001) por R$ 159,90. Quer adicionar ao carrinho?",
            tool_calls=[],
        ),
    ])
    agent = Agent(
        llm=llm,
        rag=None,
        config=AgentConfig(max_iterations=5, llm_timeout_s=10),
        data_dir=data_dir,
        pedidos_dir=tmp_path,
        system_prompt_template="sistema base\n\n{rag_context}",
    )
    out = agent.run_turn("tem mouse logitech?")
    assert "Logitech" in out
    # garante que a 2ª chamada ao LLM já recebeu o resultado da tool
    last_msgs = llm.received_messages[-1]
    assert any(m.get("role") == "tool" for m in last_msgs)
