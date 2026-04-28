"""Loop do agente — escrito à mão, sem framework. Peça avaliada do desafio."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nimbus.llm.base import ChatResponse, LLMError
from nimbus.tools.errors import ToolError
from nimbus.tools.registry import TOOL_SCHEMAS, build_context, execute_tool

log = logging.getLogger("nimbus.agent")


@dataclass
class AgentConfig:
    max_iterations: int = 5
    llm_timeout_s: float = 30.0
    rag_top_k: int = 3


class Agent:
    def __init__(
        self,
        llm: Any,
        rag: Any,
        config: AgentConfig,
        data_dir: Path,
        pedidos_dir: Path,
        system_prompt_template: str,
    ):
        self.llm = llm
        self.rag = rag  # pode ser None em testes
        self.config = config
        self.system_prompt_template = system_prompt_template
        self.ctx = build_context(data_dir=data_dir, pedidos_dir=pedidos_dir)
        self.conversation: list[dict] = []
        self.iterations_last_turn: int = 0

    def _retrieve_context(self, query: str) -> str:
        if self.rag is None:
            return "(sem contexto institucional carregado)"
        hits = self.rag.search(query, top_k=self.config.rag_top_k)
        if not hits:
            return "(nenhum trecho relevante)"
        return "\n\n".join(f"[Fonte: {h.chunk.source}]\n{h.chunk.text}" for h in hits)

    def _build_messages(self, rag_context: str) -> list[dict]:
        system_content = self.system_prompt_template.format(rag_context=rag_context)
        return [{"role": "system", "content": system_content}, *self.conversation]

    def run_turn(self, user_message: str) -> str:
        log.info("USER: %s", user_message)
        self.conversation.append({"role": "user", "content": user_message})
        rag_context = self._retrieve_context(user_message)

        for iteration in range(self.config.max_iterations):
            self.iterations_last_turn = iteration + 1
            log.info("--- iteração %d ---", iteration + 1)
            try:
                response: ChatResponse = self.llm.chat(
                    messages=self._build_messages(rag_context),
                    tools=TOOL_SCHEMAS,
                    timeout=self.config.llm_timeout_s,
                )
            except (TimeoutError, LLMError) as e:
                log.error("erro no LLM: %s", e)
                return "Desculpe, tive um problema ao consultar o assistente. Tente novamente."

            if response.tool_calls:
                # registra a mensagem do assistant com tool_calls
                self.conversation.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments if isinstance(tc.arguments, str)
                                              else json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                })
                for tc in response.tool_calls:
                    log.info("TOOL CALL: %s args=%s", tc.name, tc.arguments)
                    try:
                        result = execute_tool(tc.name, tc.arguments, self.ctx)
                        result_content = json.dumps(result, ensure_ascii=False, default=str)
                        log.info("TOOL OK: %s", result_content[:200])
                    except ToolError as e:
                        result_content = json.dumps({"error": str(e)}, ensure_ascii=False)
                        log.warning("TOOL ERROR: %s", e)
                    except Exception as e:  # noqa: BLE001
                        result_content = json.dumps({"error": f"erro inesperado: {e}"}, ensure_ascii=False)
                        log.exception("TOOL CRASH")
                    self.conversation.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": result_content,
                    })
                continue

            final = response.content or ""
            self.conversation.append({"role": "assistant", "content": final})
            log.info("FINAL: %s", final)
            return final

        log.warning("max_iterations atingido sem resposta final")
        return "Não consegui resolver em tempo. Pode reformular sua pergunta?"
