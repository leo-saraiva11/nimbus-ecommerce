"""Loop do agente — escrito à mão, sem framework. Peça avaliada do desafio."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbus.llm.base import ChatResponse, LLMError, Usage
from nimbus.tools.errors import ToolError
from nimbus.tools.registry import TOOL_SCHEMAS, build_context, execute_tool

log = logging.getLogger("nimbus.agent")

_HR = "═" * 70
_DIV = "─" * 60


@dataclass
class AgentConfig:
    max_iterations: int = 5
    llm_timeout_s: float = 30.0
    debug: bool = False


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
        self.config = config
        self.system_prompt_template = system_prompt_template
        self.ctx = build_context(data_dir=data_dir, pedidos_dir=pedidos_dir, rag=rag)
        self.conversation: list[dict] = []
        self.iterations_last_turn: int = 0
        self._turn_counter: int = 0
        self.total_usage: Usage = Usage()
        self.last_turn_usage: Usage = Usage()

    # ---------------------------------------------------------------- trace --

    def _trace(self, *lines: str) -> None:
        if not self.config.debug:
            return
        for line in lines:
            print(line, flush=True)

    def _section(self, title: str) -> None:
        self._trace(f"  ── {title} {_DIV[: max(0, 60 - len(title) - 1)]}")

    def _trace_llm_request(self, messages: list[dict]) -> None:
        if not self.config.debug:
            return
        self._trace(
            f"  → LLM request  (mensagens={len(messages)}, "
            f"tools={len(TOOL_SCHEMAS)}, timeout={self.config.llm_timeout_s}s)"
        )

    def _trace_llm_response(self, response: ChatResponse, elapsed_ms: float) -> None:
        if not self.config.debug:
            return
        usage = response.usage
        usage_str = ""
        if usage:
            usage_str = (
                f", tokens prompt={usage.prompt_tokens} "
                f"completion={usage.completion_tokens} total={usage.total_tokens}"
            )
        self._trace(f"  ← LLM response  ({elapsed_ms:.0f}ms{usage_str})")
        content = response.content or "(vazio)"
        if len(content) > 300:
            content = content[:300] + "…"
        self._trace(f"     content: {content}")
        if response.tool_calls:
            self._trace(f"     tool_calls ({len(response.tool_calls)}):")
            for tc in response.tool_calls:
                args_repr = tc.arguments if isinstance(tc.arguments, str) else json.dumps(tc.arguments, ensure_ascii=False)
                self._trace(f"       [{tc.id}] {tc.name}({args_repr})")
        else:
            self._trace("     tool_calls: (nenhuma)")

    def _trace_tool(self, name: str, args: Any, result_content: str, elapsed_ms: float, status: str) -> None:
        if not self.config.debug:
            return
        args_repr = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
        marker = "⚙" if status == "ok" else ("✗" if status == "error" else "💥")
        self._trace(f"  {marker} TOOL {name}  ({elapsed_ms:.0f}ms, {status})")
        self._trace(f"     args:   {args_repr}")
        self._trace(f"     result: {result_content}")

    def _trace_turn_summary(self) -> None:
        if not self.config.debug:
            return
        u = self.last_turn_usage
        t = self.total_usage
        self._trace(
            f"  Σ tokens neste turno: prompt={u.prompt_tokens} "
            f"completion={u.completion_tokens} total={u.total_tokens}",
            f"  Σ tokens acumulados:  prompt={t.prompt_tokens} "
            f"completion={t.completion_tokens} total={t.total_tokens}",
        )

    # ------------------------------------------------------------------ loop --

    def run_turn(self, user_message: str) -> str:
        self._turn_counter += 1
        self._trace(_HR, f"  TURNO #{self._turn_counter}", _HR, f"  USER: {user_message}", "")

        log.info("USER: %s", user_message)
        self.conversation.append({"role": "user", "content": user_message})

        # system prompt sem mais injeção automática de RAG: o modelo decide
        # chamar a tool search_policies quando a pergunta for institucional.
        messages_template = self._build_messages()
        self.last_turn_usage = Usage()

        for iteration in range(self.config.max_iterations):
            self.iterations_last_turn = iteration + 1
            log.info("--- iteração %d ---", iteration + 1)
            self._trace("", f"  ── Iteração {iteration + 1} {_DIV[: 60 - len(f'Iteração {iteration + 1}') - 1]}")
            messages = self._build_messages()
            self._trace_llm_request(messages)

            t0 = time.monotonic()
            try:
                response: ChatResponse = self.llm.chat(
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    timeout=self.config.llm_timeout_s,
                )
            except (TimeoutError, LLMError) as e:
                log.error("erro no LLM: %s", e)
                self._trace(f"  ✗ LLM ERROR: {e}", _HR, "")
                return "Desculpe, tive um problema ao consultar o assistente. Tente novamente."
            elapsed_llm = (time.monotonic() - t0) * 1000

            if response.usage:
                self.last_turn_usage = self.last_turn_usage + response.usage
                self.total_usage = self.total_usage + response.usage

            self._trace_llm_response(response, elapsed_llm)

            if response.tool_calls:
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
                    t1 = time.monotonic()
                    status = "ok"
                    try:
                        result = execute_tool(tc.name, tc.arguments, self.ctx)
                        result_content = json.dumps(result, ensure_ascii=False, default=str)
                        log.info("TOOL OK: %s", result_content)
                    except ToolError as e:
                        status = "error"
                        result_content = json.dumps({"error": str(e)}, ensure_ascii=False)
                        log.warning("TOOL ERROR: %s", e)
                    except Exception as e:  # noqa: BLE001
                        status = "crash"
                        result_content = json.dumps({"error": f"erro inesperado: {e}"}, ensure_ascii=False)
                        log.exception("TOOL CRASH")
                    elapsed_tool = (time.monotonic() - t1) * 1000
                    self._trace_tool(tc.name, tc.arguments, result_content, elapsed_tool, status)
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
            self._trace("", f"  ✓ FINAL: {final}")
            self._trace_turn_summary()
            self._trace(_HR, "")
            return final

        log.warning("max_iterations atingido sem resposta final")
        self._trace("", f"  ✗ max_iterations ({self.config.max_iterations}) atingido sem resposta final")
        self._trace_turn_summary()
        self._trace(_HR, "")
        return "Não consegui resolver em tempo. Pode reformular sua pergunta?"

    # --------------------------------------------------------------- helpers --

    def _build_messages(self) -> list[dict]:
        # mantém compatibilidade com prompts que usam {rag_context}
        # (passa string vazia — RAG agora é tool, o modelo busca quando precisa)
        try:
            system_content = self.system_prompt_template.format(rag_context="")
        except (KeyError, IndexError):
            system_content = self.system_prompt_template
        return [{"role": "system", "content": system_content}, *self.conversation]
