import pytest
from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


class AlwaysToolCallLLM:
    """Mock LLM que sempre devolve uma tool call (vai forçar max_iter)."""

    def chat(self, messages, tools, timeout):
        return ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="view_cart", arguments="{}")],
        )


def test_loop_para_em_max_iterations(data_dir, tmp_path):
    agent = Agent(
        llm=AlwaysToolCallLLM(),
        rag=None,
        config=AgentConfig(max_iterations=3, llm_timeout_s=10),
        data_dir=data_dir,
        pedidos_dir=tmp_path,
        system_prompt_template="sistema base\n\n{rag_context}",
    )
    out = agent.run_turn("oi")
    assert "tempo" in out.lower() or "reformular" in out.lower()
    # confirma que rodou exatamente 3 vezes a tool
    assert agent.iterations_last_turn == 3
