# Nimbus — Agente Conversacional de E-commerce

Mini-agente CLI que conversa com o usuário pra ajudá-lo a montar um carrinho na loja fictícia **Loja Nimbus** (e-commerce de eletrônicos), consulta CSVs via tools, busca políticas em texto via RAG, e gera um relatório markdown final do pedido.

Desafio prático Fase 3 — Vaga Dev de Agentes e Automação.

## Provider de LLM

Padrão: **Groq** (`llama-3.3-70b-versatile`). O free tier é suficiente. A interface `LLMClient` (em `nimbus/llm/base.py`) é desacoplada — pra trocar pra OpenRouter, Anthropic ou Ollama, basta criar um novo `*_client.py` implementando o Protocol e ajustar uma linha no `cli.py`.

## Setup

Requer Python 3.11+.

```bash
git clone <este-repo>
cd nimbus_ecommerce
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edite .env e cole sua GROQ_API_KEY (https://console.groq.com)
```

## Como rodar

```bash
python -m nimbus              # modo normal
python -m nimbus --debug      # trace completo de cada turno
python -m nimbus -d           # equivalente curto
```

Primeiro start baixa o modelo de embeddings `all-MiniLM-L6-v2` (~80MB).

### Modo `--debug`

Imprime, a cada pergunta, um trace estruturado de tudo que o agente faz por baixo dos panos:

- **RAG retrieval**: os chunks recuperados, com score e nome do arquivo de origem.
- **Iterações do loop**: para cada iteração, a request ao LLM (nº de mensagens, tools, timeout) e a response (`content` + `tool_calls` com argumentos completos).
- **Tools**: nome, args, **resultado completo sem truncamento**, duração e status (`ok`/`error`/`crash`).
- **Resposta final** ao usuário.

Exemplo de saída em modo debug:

```
══════════════════════════════════════════════════════════════════════
  TURNO #1
══════════════════════════════════════════════════════════════════════
  USER: tem produtos da logitech?

  ── RAG retrieval (top 3) ──────────────────────────────────────
  [1] score=0.812  fonte=politica_trocas_devolucoes.md
      Direito de arrependimento em 7 dias corridos para devoluções.
  ...

  ── Iteração 1 ─────────────────────────────────────────────────
  → LLM request  (mensagens=2, tools=8, timeout=30.0s)
  ← LLM response  (842ms)
     content: (vazio)
     tool_calls (1):
       [t1] search_products({"query": "logitech"})
  ⚙ TOOL search_products  (3ms, ok)
     args:   {"query": "logitech"}
     result: [{"id": "P001", "nome": "Mouse Gamer Logitech G203", ...}, ...]

  ── Iteração 2 ─────────────────────────────────────────────────
  → LLM request  (mensagens=4, tools=8, timeout=30.0s)
  ← LLM response  (1124ms)
     content: Encontrei 2 produtos Logitech: o Mouse G203 (R$ 159,90)...
     tool_calls: (nenhuma)

  ✓ FINAL: Encontrei 2 produtos Logitech: o Mouse G203 (R$ 159,90)...
══════════════════════════════════════════════════════════════════════
```

A flag também ativa logging em nível `INFO` no `logging` padrão (mesmo efeito de `NIMBUS_DEBUG=1`).

## Testes

```bash
pytest -v
```

## Arquitetura do loop

O **loop do agente** está em `nimbus/agent.py:run_turn`. Ele é escrito à mão (sem LangChain/CrewAI/Agno):

1. Adiciona a mensagem do usuário ao histórico.
2. Recupera top-3 chunks RAG do corpus para a pergunta.
3. Em cada iteração (até `MAX_ITERATIONS=5`):
   - Chama o LLM com o histórico + tool schemas.
   - Se resposta tem `tool_calls`: executa cada tool localmente, anexa resultado como mensagem `role=tool`, segue pra próxima iteração.
   - Se resposta é texto final: retorna.
4. Se estourar o limite, retorna fallback amigável.

### Guardas obrigatórias

- `MAX_ITERATIONS = 5`
- `LLM_TIMEOUT_S = 30`
- `try/except ToolError` → erro estruturado (`{"error": "..."}`) devolvido ao modelo, que decide o próximo passo.
- Logging estruturado de cada iteração: pergunta do usuário, tool_calls com argumentos, resultados das tools, resposta final. Para inspecionar tudo em runtime, rode com `--debug` (ou `-d`) — ver seção acima.

## Tools disponíveis (8)

| Tool | Função |
|---|---|
| `search_products(query, categoria?, max_preco?)` | Busca no catálogo |
| `get_product(id)` | Detalhes de 1 produto |
| `validate_coupon(codigo, valor_pedido)` | Valida cupom |
| `calculate_shipping(uf, valor_pedido)` | Calcula frete (50% off acima R$500) |
| `add_to_cart(produto_id, quantidade)` | Adiciona ao carrinho |
| `view_cart()` | Mostra carrinho |
| `remove_from_cart(produto_id)` | Remove do carrinho |
| `generate_order_report(uf, cupom?)` | Gera markdown final em `pedidos/` |

## Decisões de chunking (RAG)

- **Chunking por parágrafo** com overlap de 1 parágrafo. Os docs do corpus são curtos (~10-20 parágrafos cada), então chunking sofisticado seria overkill — parágrafos casam bem com a granularidade das perguntas.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`, multilíngue suficiente, roda local (zero custo, zero rede após o primeiro download).
- **Store**: in-memory com cosine similarity em `numpy`. Para 4 docs × ~15 chunks = ~60 vetores, qualquer DB seria over-engineering.
- **Retrieval**: top_k=3, sem reranking.

## Bônus implementados

- ✅ Abstração `LLMClient` (trocar provider = trocar arquivo)
- ✅ Memória multi-turno (necessária pro fluxo de carrinho)
- ✅ Citação de fonte no RAG (instruída no system prompt)

## Fora de escopo

- Streaming de resposta
- Persistência de histórico/carrinho em DB
- RAG avançado (reranking, HyDE)
- UI gráfica/web

## Estrutura

```
data/        CSVs (catálogo, cupons, frete)
corpus/      Docs institucionais (.md) consultados via RAG
nimbus/
  llm/       Interface LLMClient + GroqClient
  rag/       Chunker, embeddings, store
  tools/     Implementações das 8 tools + registry
  agent.py   LOOP PRÓPRIO
  cli.py     REPL
tests/       4 grupos de testes (parsing, max_iter, integração, tools)
pedidos/     Relatórios gerados (gitignored)
```
