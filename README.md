# Nimbus — Agente Conversacional de E-commerce

Mini-agente CLI que conversa com o usuário pra ajudá-lo a montar um carrinho na loja fictícia **Loja Nimbus** (e-commerce de eletrônicos), consulta CSVs via tools, busca políticas em texto via RAG-como-tool, e gera um relatório markdown final do pedido.

Desafio prático Fase 3 — Vaga Dev de Agentes e Automação.

## Provider de LLM

Suporta dois providers prontos:

| Provider | Modelo padrão | Como ligar |
|---|---|---|
| **Groq** (padrão) | `llama-3.3-70b-versatile` | `GROQ_API_KEY` no `.env` |
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct` | `OPENROUTER_API_KEY` + `NIMBUS_PROVIDER=openrouter` |

A interface `LLMClient` (em `nimbus/llm/base.py`) é desacoplada — adicionar Anthropic/Ollama é criar mais um arquivo `*_client.py` implementando o Protocol e dispatchar no `cli._build_llm`.

## Setup

Requer Python 3.11+.

```bash
git clone <este-repo>
cd recria-ai
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edite .env e cole sua GROQ_API_KEY (ou OPENROUTER_API_KEY)
```

## Como rodar

```bash
python -m nimbus                          # Groq, modo normal
python -m nimbus --debug                  # Groq, com trace completo
python -m nimbus -d                       # equivalente curto
python -m nimbus --provider openrouter    # OpenRouter
python -m nimbus --provider openrouter -d # OpenRouter + debug
```

Primeiro start baixa o modelo de embeddings `all-MiniLM-L6-v2` (~80MB).

### Modo `--debug`

Imprime, a cada pergunta, um trace estruturado de tudo que o agente faz por baixo dos panos:

- **Iterações do loop**: para cada iteração, a request ao LLM (nº de mensagens, tools, timeout) e a response (`content` + `tool_calls` com argumentos completos), com **tokens consumidos** quando o provider expõe (`prompt`, `completion`, `total`).
- **Tools**: nome, args, **resultado completo sem truncamento**, duração e status (`ok`/`error`/`crash`). Inclui `search_policies` (RAG) com score e fonte de cada chunk retornado.
- **Resumo do turno**: tokens consumidos no turno + acumulado total da sessão.
- **Resposta final** ao usuário.

Exemplo de saída em modo debug (pergunta institucional):

```
══════════════════════════════════════════════════════════════════════
  TURNO #1
══════════════════════════════════════════════════════════════════════
  USER: posso devolver um produto?

  ── Iteração 1 ─────────────────────────────────────────────────
  → LLM request  (mensagens=2, tools=9, timeout=30.0s)
  ← LLM response  (842ms, tokens prompt=150 completion=18 total=168)
     content: (vazio)
     tool_calls (1):
       [t1] search_policies({"query": "devolver produto", "top_k": 3})
  ⚙ TOOL search_policies  (3ms, ok)
     args:   {"query": "devolver produto", "top_k": 3}
     result: [{"fonte": "politica_trocas_devolucoes.md", "score": 0.892,
               "trecho": "Direito de arrependimento em 7 dias..."}]

  ── Iteração 2 ─────────────────────────────────────────────────
  → LLM request  (mensagens=4, tools=9, timeout=30.0s)
  ← LLM response  (1124ms, tokens prompt=420 completion=45 total=465)
     content: Sim, você pode devolver em até 7 dias corridos
              (fonte: politica_trocas_devolucoes.md).
     tool_calls: (nenhuma)

  ✓ FINAL: Sim, você pode devolver em até 7 dias...
  Σ tokens neste turno: prompt=570 completion=63 total=633
  Σ tokens acumulados:  prompt=570 completion=63 total=633
══════════════════════════════════════════════════════════════════════
```

A flag também sobe o nível do logger no console pra `INFO` (mesmo efeito de `NIMBUS_DEBUG=1`).

### Logs em arquivo

Cada sessão CLI grava um arquivo em `logs/session_YYYYMMDD_HHMMSS.log`, **sempre em nível `INFO`** (independente de `--debug`). O caminho é impresso na partida:

```
[setup] log da sessão: /caminho/recria-ai/logs/session_20260428_161631.log
```

O arquivo registra os 4 eventos exigidos pelo desafio para cada turno: pergunta do usuário (`USER:`), tool call do modelo (`TOOL CALL:` com args), resultado da tool (`TOOL OK/ERROR/CRASH:` com payload completo), resposta final (`FINAL:`). O console mantém o nível `WARNING` por padrão (limpo); usar `--debug` espelha tudo no terminal também.

Os arquivos são gitignored (`logs/`) — nada vai pro repo.

## Testes

```bash
pytest -v
```

46 testes cobrindo: parsing de tool calls, parada do loop em `max_iterations`, integração com mock de LLMClient, todas as tools (catalog, pricing, cart, report, search_policies), RAG (chunker, store), modo debug e tracking de tokens.

## Arquitetura do loop

O **loop do agente** está em `nimbus/agent.py:run_turn`. Escrito à mão, sem LangChain/CrewAI/Agno:

1. Adiciona a mensagem do usuário ao histórico de conversa.
2. Em cada iteração (até `MAX_ITERATIONS=5`):
   - Monta as mensagens (system prompt + histórico) e chama o LLM com `TOOL_SCHEMAS`.
   - Se a resposta tem `tool_calls`: executa cada tool localmente via `execute_tool(name, args, ctx)`, anexa o resultado ao histórico como `role=tool`, e segue pra próxima iteração.
   - Se a resposta é texto final: retorna pro usuário.
3. Se estourar `MAX_ITERATIONS`, retorna fallback amigável.

**RAG não é injetado automaticamente.** O modelo decide consultar a base institucional via tool `search_policies` quando a pergunta é sobre regras/políticas. Isso evita ruído em perguntas de catálogo (`"tem mouse logitech?"` não puxa chunks de devolução).

### Guardas obrigatórias

- `MAX_ITERATIONS = 5`
- `LLM_TIMEOUT_S = 30`
- `try/except ToolError` → erro estruturado (`{"error": "..."}`) devolvido ao modelo, que decide o próximo passo.
- `try/except Exception` (inesperado) → log + payload genérico de erro. Distingue erro esperado (vai pro modelo) de crash (loga e segue).
- Logging estruturado por iteração: pergunta do usuário, tool_calls com argumentos, resultados das tools, resposta final.
- **Janela de histórico** (`AgentConfig.history_turns=7`): apenas os últimos 7 turnos vão pro LLM em cada chamada (cortando sempre em borda de `role=user`, sem quebrar o protocolo de tool use). O histórico completo segue em `Agent.conversation` para logs e debug. Configurável: 0 ou negativo desliga a janela.

## Tools disponíveis (9)

| Tool | Função | Fonte |
|---|---|---|
| `search_products(query, categoria?, max_preco?)` | Busca no catálogo | `data/produtos.csv` |
| `get_product(id)` | Detalhes de 1 produto | `data/produtos.csv` |
| `validate_coupon(codigo, valor_pedido)` | Valida cupom | `data/cupons.csv` |
| `calculate_shipping(uf, valor_pedido)` | Calcula frete (50% off acima R$500) | `data/frete.csv` |
| `add_to_cart(produto_id, quantidade)` | Adiciona ao carrinho | estado em memória |
| `view_cart()` | Mostra carrinho | estado em memória |
| `remove_from_cart(produto_id)` | Remove do carrinho | estado em memória |
| `generate_order_report(uf, cupom?)` | Gera markdown final em `pedidos/` | tudo |
| `search_policies(query, top_k?)` | RAG sobre políticas (trocas, pagamento, entrega, garantia) | `corpus/*.md` |

## Decisões de RAG

- **RAG-como-tool** (`search_policies`) em vez de injeção automática no system prompt — o modelo decide quando consultar políticas, evitando ruído.
- **Chunking por parágrafo** com overlap de 1 parágrafo. Os docs do corpus são curtos (~10-20 parágrafos cada), então chunking sofisticado seria overkill.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`, roda local (zero custo, zero rede após primeiro download).
- **Store**: in-memory com cosine similarity em `numpy`. ~60 vetores → qualquer DB seria over-engineering.
- **Retrieval**: top_k configurável pelo modelo (padrão 3, máx 5), sem reranking.

## Bônus implementados

- ✅ Abstração `LLMClient` (Groq + OpenRouter prontos, novos providers em ~30 linhas)
- ✅ Memória multi-turno (necessária pro fluxo de carrinho)
- ✅ Citação de fonte no RAG (instruída no system prompt + retornada no payload da tool)
- ✅ Tracking de tokens (`Usage` por response + acumulado por turno e sessão, exibido em modo debug)

## Persistência (o que é local)

Tudo é local exceto a chamada ao LLM:

| O que | Onde | Persiste entre sessões? |
|---|---|---|
| Chamada ao LLM | Groq/OpenRouter API (rede) | — |
| Modelo de embeddings | `~/.cache/huggingface/` (cache do `sentence-transformers`) | sim, baixado 1ª vez |
| Vetores RAG | in-memory (`VectorStore`) | não — reindexado a cada start |
| Catálogo, cupons, frete | `data/*.csv` | sim |
| Corpus institucional | `corpus/*.md` | sim |
| Conversa multi-turno | in-memory (`Agent.conversation`) | não — fora de escopo |
| Carrinho | in-memory (`CartState`) | não — idem |
| Relatório do pedido | `pedidos/pedido_<timestamp>.md` | sim (gitignored) |
| Logs da sessão | `logs/session_<timestamp>.log` | sim (gitignored) |
| API keys | `.env` | sim (gitignored) |

Zero DB, zero cloud storage. Único tráfego de rede é a chamada HTTP pro LLM.

## Fora de escopo

- Streaming de resposta
- Persistência de histórico/carrinho em DB
- RAG avançado (reranking, HyDE)
- UI gráfica/web

## Estrutura

```
data/                  CSVs (catálogo, cupons, frete)
corpus/                Docs institucionais consultados via search_policies
nimbus/
  llm/                 Interface LLMClient + GroqClient + OpenRouterClient
  rag/                 Chunker, embeddings, vector store
  tools/               Implementações das 9 tools + registry/dispatcher
  prompts/system.md    Instruções pro LLM (quando usar cada tool)
  agent.py             LOOP PRÓPRIO (peça avaliada)
  cli.py               REPL com argparse + seleção de provider
tests/                 46 testes (TDD por task)
pedidos/               Relatórios gerados (gitignored)
docs/superpowers/      Spec + plano de implementação
```
