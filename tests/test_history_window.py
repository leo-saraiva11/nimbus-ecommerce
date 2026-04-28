"""Janela deslizante: só os últimos N turnos vão pro LLM, mas o histórico completo
permanece em Agent.conversation pra logs e debug."""
from __future__ import annotations
import json

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


class _RecordingLLM:
    """Captura cada lista de mensagens enviada — pra verificar o que foi cortado."""

    def __init__(self):
        self.received = []

    def chat(self, messages, tools, timeout):
        self.received.append(list(messages))
        return ChatResponse(content="ok", tool_calls=[])


def _make_agent(llm, history_turns, data_dir, tmp_path):
    return Agent(
        llm=llm, rag=None,
        config=AgentConfig(max_iterations=3, history_turns=history_turns),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis",
    )


def test_history_window_corta_turnos_antigos(data_dir, tmp_path):
    """Com 8 turnos no histórico e janela=7, o LLM recebe só os últimos 7."""
    llm = _RecordingLLM()
    agent = _make_agent(llm, history_turns=7, data_dir=data_dir, tmp_path=tmp_path)
    for i in range(8):
        agent.run_turn(f"pergunta {i + 1}")

    # histórico completo tem 16 mensagens (8 user + 8 assistant)
    assert len(agent.conversation) == 16

    # ÚLTIMA chamada ao LLM (do 8º turno) deve carregar só 7 user messages
    last_msgs = llm.received[-1]
    user_msgs = [m for m in last_msgs if m.get("role") == "user"]
    assert len(user_msgs) == 7
    # primeiro user enviado deve ser "pergunta 2" (turno 1 ficou de fora)
    assert user_msgs[0]["content"] == "pergunta 2"
    assert user_msgs[-1]["content"] == "pergunta 8"


def test_history_window_nao_corta_se_dentro_do_limite(data_dir, tmp_path):
    """3 turnos com janela=7 → nada cortado."""
    llm = _RecordingLLM()
    agent = _make_agent(llm, history_turns=7, data_dir=data_dir, tmp_path=tmp_path)
    for i in range(3):
        agent.run_turn(f"q{i}")
    last_msgs = llm.received[-1]
    user_msgs = [m for m in last_msgs if m.get("role") == "user"]
    assert len(user_msgs) == 3


def test_history_turns_zero_ou_negativo_desliga_janela(data_dir, tmp_path):
    llm = _RecordingLLM()
    agent = _make_agent(llm, history_turns=0, data_dir=data_dir, tmp_path=tmp_path)
    for i in range(10):
        agent.run_turn(f"q{i}")
    last_msgs = llm.received[-1]
    user_msgs = [m for m in last_msgs if m.get("role") == "user"]
    assert len(user_msgs) == 10  # todos preservados


def test_history_window_corta_em_borda_de_user_message(data_dir, tmp_path):
    """Janela DEVE cortar em borda de role=user — nunca entre assistant(tool_calls)
    e seu tool result (isso quebraria o protocolo do OpenAI/Groq)."""

    class _ScriptedLLM:
        def __init__(self, responses):
            self._responses = list(responses)
            self.received = []

        def chat(self, messages, tools, timeout):
            self.received.append(list(messages))
            return self._responses.pop(0)

    # cada turno: 1 tool_call + 1 final  (ciclo padrão de 2 chamadas ao LLM)
    responses = []
    for _ in range(8):
        responses.append(ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="tx", name="get_product",
                                 arguments=json.dumps({"produto_id": "P001"}))],
        ))
        responses.append(ChatResponse(content="ok", tool_calls=[]))

    llm = _ScriptedLLM(responses)
    agent = _make_agent(llm, history_turns=3, data_dir=data_dir, tmp_path=tmp_path)
    for i in range(8):
        agent.run_turn(f"q{i}")

    last_msgs = llm.received[-1]
    # primeiro item depois do system DEVE ser role=user (borda limpa)
    after_system = [m for m in last_msgs if m.get("role") != "system"]
    assert after_system[0]["role"] == "user"

    # protocolo: cada tool_call_id em mensagens role=tool deve ter um assistant
    # com aquele id em tool_calls antes dele
    assistant_tc_ids = set()
    for m in last_msgs:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                assistant_tc_ids.add(tc["id"])
        if m.get("role") == "tool":
            assert m["tool_call_id"] in assistant_tc_ids, "tool órfã na janela"


def test_full_conversation_preservada_em_memoria(data_dir, tmp_path):
    """Histórico completo continua em Agent.conversation mesmo com janela ativa."""
    llm = _RecordingLLM()
    agent = _make_agent(llm, history_turns=2, data_dir=data_dir, tmp_path=tmp_path)
    for i in range(5):
        agent.run_turn(f"pergunta {i + 1}")
    # 5 turnos × 2 mensagens cada = 10
    assert len(agent.conversation) == 10
    user_full = [m for m in agent.conversation if m["role"] == "user"]
    assert [m["content"] for m in user_full] == [f"pergunta {i + 1}" for i in range(5)]
