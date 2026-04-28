"""Garante que cada sessão CLI gera um arquivo de log com os eventos do turno."""
from __future__ import annotations
import json
import logging

from nimbus.agent import Agent, AgentConfig
from nimbus.cli import _setup_logging
from nimbus.llm.base import ChatResponse, ToolCall


class _ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def chat(self, messages, tools, timeout):
        return self._responses.pop(0)


def test_setup_logging_cria_arquivo_em_logs_dir(tmp_path):
    log_file = _setup_logging(verbose=False, logs_dir=tmp_path)
    assert log_file.parent == tmp_path
    assert log_file.exists()
    assert log_file.name.startswith("session_")
    assert log_file.suffix == ".log"


def test_arquivo_de_log_registra_eventos_do_turno(tmp_path, data_dir):
    """Os 4 eventos exigidos pelo desafio devem aparecer no arquivo de log."""
    log_file = _setup_logging(verbose=False, logs_dir=tmp_path)

    llm = _ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="get_product",
                                 arguments=json.dumps({"produto_id": "P001"}))],
        ),
        ChatResponse(content="Mouse Logitech G203 por R$ 159,90.", tool_calls=[]),
    ])
    agent = Agent(
        llm=llm, rag=None,
        config=AgentConfig(max_iterations=5),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis",
    )
    agent.run_turn("detalhes do P001")

    # força flush dos handlers
    for h in logging.getLogger().handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    # 1) pergunta do usuário
    assert "USER: detalhes do P001" in content
    # 2) tool call do modelo (com args)
    assert "TOOL CALL: get_product" in content
    assert "P001" in content
    # 3) resultado da tool (não truncado)
    assert "TOOL OK:" in content
    assert "Mouse Gamer Logitech G203" in content
    assert "descricao_curta" in content
    # 4) resposta final
    assert "FINAL: Mouse Logitech G203" in content


def test_log_console_silencioso_quando_verbose_false(tmp_path, data_dir, capfd):
    """Sem verbose, console fica em WARNING — INFO só vai pro arquivo."""
    _setup_logging(verbose=False, logs_dir=tmp_path)

    llm = _ScriptedLLM([ChatResponse(content="oi", tool_calls=[])])
    agent = Agent(
        llm=llm, rag=None,
        config=AgentConfig(),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis",
    )
    agent.run_turn("oi")
    err = capfd.readouterr().err
    # nenhum log de INFO deve aparecer no stderr (USER/TOOL CALL/FINAL etc.)
    assert "INFO" not in err
    assert "FINAL:" not in err


def test_log_console_verbose_nao_polui_stderr(tmp_path, data_dir, capfd):
    """Mesmo com verbose=True, o console (stderr) fica em WARNING — o trace
    visual (stdout, controlado por AgentConfig.debug) é a fonte de info."""
    _setup_logging(verbose=True, logs_dir=tmp_path)

    llm = _ScriptedLLM([ChatResponse(content="oi", tool_calls=[])])
    agent = Agent(
        llm=llm, rag=None,
        config=AgentConfig(),
        data_dir=data_dir, pedidos_dir=tmp_path,
        system_prompt_template="sis",
    )
    agent.run_turn("oi")
    err = capfd.readouterr().err
    assert "USER: oi" not in err
    assert "FINAL: oi" not in err


def test_libs_ruidosas_silenciadas(tmp_path):
    """httpx e demais libs barulhentas devem ficar em WARNING ou acima."""
    _setup_logging(verbose=False, logs_dir=tmp_path)
    for name in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        assert logging.getLogger(name).level >= logging.WARNING
