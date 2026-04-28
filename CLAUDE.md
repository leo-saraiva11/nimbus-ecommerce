# CLAUDE.md

Guia rápido para o Claude Code trabalhar neste repositório de forma produtiva.

## O que é este projeto

Agente conversacional CLI ("Nimbus") para um e-commerce fictício de eletrônicos. Entregável de um desafio prático de vaga de Dev de Agentes e Automação.

**Restrição central** (não-negociável): o loop do agente é escrito à mão em `nimbus/agent.py`. **NÃO use** LangChain Agents, CrewAI, Agno ou qualquer framework que abstraia o loop tool-use → execução → resposta. O grader vai verificar exatamente isso.

## Comandos essenciais

```bash
# venv (Python 3.11+; o repo foi desenvolvido com 3.12)
source .venv/bin/activate

# install (editable + dev deps)
pip install -e ".[dev]"

# rodar a CLI
python -m nimbus                          # Groq, modo normal
python -m nimbus -d                       # com trace completo
python -m nimbus --provider openrouter    # OpenRouter

# testes
pytest                # ~46 testes, deve ficar verde
pytest -v             # verbose
pytest tests/test_agent_debug.py -v   # arquivo específico
```

## Layout

```
data/                  CSVs do "banco" (produtos, cupons, frete)
corpus/                4 docs .md consultados via search_policies (RAG)
nimbus/
  llm/                 LLMClient (Protocol) + GroqClient + OpenRouterClient
  rag/                 chunker.py, embeddings.py (sentence-transformers), store.py (cosine in-memory)
  tools/               9 tools + registry/dispatcher
  prompts/system.md    Instruções para o LLM
  agent.py             Loop próprio (peça central)
  cli.py               argparse + REPL
tests/                 TDD-driven, 1 arquivo por área
pedidos/               Relatórios markdown gerados em runtime (gitignored)
docs/superpowers/
  specs/               Design document
  plans/               Plano de implementação task-a-task
```

## Convenções

### Tool design

- Cada tool é uma função pura em `nimbus/tools/<area>.py`. Estado (cart, dados) entra como argumento explícito.
- Erros esperados (produto não existe, cupom expirado, estoque insuficiente) levantam `ToolError` (de `nimbus/tools/errors.py`). O loop em `agent.py` captura e devolve `{"error": "..."}` ao LLM como mensagem `role=tool`, e o modelo decide como reagir.
- Schemas JSON de tools ficam em `nimbus/tools/registry.py:TOOL_SCHEMAS` (formato OpenAI/Groq tool calling).
- Para adicionar tool nova: implementação em `tools/<area>.py` → schema em `TOOL_SCHEMAS` → branch no `execute_tool()` → testes em `tests/test_<area>.py`.

### RAG

- **Não injetar RAG automaticamente no system prompt.** O modelo chama `search_policies(query, top_k?)` quando vê que a pergunta é institucional (políticas, prazos, regras). Esse design evita que perguntas de catálogo puxem chunks irrelevantes.
- Vector store é in-memory (`nimbus/rag/store.py`), reconstruído a cada start da CLI. Não persistir índice em disco — escopo do desafio.

### Loop do agente

Mantenha estas guardas em qualquer mudança em `agent.py:run_turn`:

| Guarda | Onde | Por quê |
|---|---|---|
| `MAX_ITERATIONS=5` | `AgentConfig`, usado no `for` | Requisito explícito do desafio |
| `LLM_TIMEOUT_S=30` | `AgentConfig`, passado pro `llm.chat` | Requisito explícito do desafio |
| `try/except ToolError` | dentro do laço de tool calls | Erro esperado vai pro modelo |
| `try/except Exception` | mesmo bloco, captura pegou ToolError | Crash inesperado vira payload genérico |
| Tokens em `Usage` | `ChatResponse.usage` populado pelos clients | Visibilidade no debug + telemetria |
| Memória multi-turno | `self.conversation: list[dict]` | Necessária pro fluxo de carrinho |

### Provider abstraction

- `nimbus/llm/base.py:LLMClient` é um `Protocol`. Adicionar provider novo = criar `nimbus/llm/<nome>_client.py` com método `chat(messages, tools, timeout) -> ChatResponse`.
- Qualquer client deve preencher `ChatResponse.usage` quando o provider expuser (Groq e OpenRouter expõem; Ollama não).
- Selecionar provider: `--provider {groq|openrouter}` ou `NIMBUS_PROVIDER` no `.env`. Dispatch em `cli._build_llm`.

### Testes

- TDD: novo recurso → teste falhando → implementação → teste verde → commit.
- Mocks de LLM: `ScriptedLLM`/`AlwaysToolCallLLM` em `tests/test_agent_*.py`. Não importar SDK real em testes.
- Embeddings reais (sentence-transformers) **não** rodam em testes — usar `FakeEmbedder` ou `_StubRAG` (ver `tests/test_rag_store.py`, `tests/test_agent_debug.py`).
- Testes de tool dispatch usam `tmp_path` pra `pedidos_dir` — nunca escrever em `pedidos/` real.

### Commits

- Conventional commits em português. Granularidade: 1 commit por mudança lógica (ver histórico de `git log`).
- Co-author footer ao final quando o commit é gerado por agente IA.
- Nunca usar `--no-verify` ou `--amend` em commits já criados — fazer commit novo.

## Arquivos importantes

| Arquivo | Por quê |
|---|---|
| `nimbus/agent.py` | **Peça avaliada do desafio.** Loop próprio com guardas. |
| `nimbus/tools/registry.py` | Tool schemas + dispatcher. Mexer aqui ao adicionar/remover tools. |
| `nimbus/prompts/system.md` | Instruções pro LLM sobre quando usar cada tool. Ajustar aqui se modelo escolher tool errada. |
| `tests/test_loop_max_iter.py` | Garante max_iter funciona. |
| `tests/test_agent_integration.py` | Garante o ciclo tool-call → result → final response. |
| `tests/test_agent_debug.py` | Garante trace + token tracking + RAG-as-tool. |
| `docs/superpowers/specs/2026-04-28-ecommerce-agent-design.md` | Design document. |
| `docs/superpowers/plans/2026-04-28-ecommerce-agent-plan.md` | Plano de implementação task-a-task (referência histórica). |
| `RELATO_IA.md` | Reflexão sobre uso de IA no desafio (entregável obrigatório). |

## O que NÃO fazer

- Não introduzir frameworks que abstraiam o loop (LangChain Agents, CrewAI, Agno, etc.).
- Não persistir carrinho/conversa em DB — fora de escopo.
- Não adicionar streaming, reranking de RAG, ou outras features fora dos bônus já implementados.
- Não truncar resultados de tools no modo debug — o ponto é mostrar tudo.
- Não silenciar `ToolError` — sempre devolver ao modelo como `{"error": ...}`.
