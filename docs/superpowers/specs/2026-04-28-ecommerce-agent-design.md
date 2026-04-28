# Nimbus — Agente Conversacional de E-commerce

**Data:** 2026-04-28
**Contexto:** Desafio prático Fase 3 — Vaga Dev de Agentes e Automação
**Escopo:** Mini-agente conversacional CLI sobre um corpus pequeno + tools próprias, com loop manual (sem framework de agente).

---

## 1. Objetivo

Construir um agente CLI que:
- Conversa com o usuário ao longo de múltiplos turnos para ajudá-lo a montar um carrinho na loja fictícia **Loja Nimbus** (e-commerce de eletrônicos).
- Consulta dados estruturados (CSVs) via tools determinísticas e textos institucionais via RAG.
- Ao final, gera um **relatório markdown** completo do pedido salvo em arquivo.

A entrega prioriza demonstrar domínio do **loop de agente escrito à mão**, com guardas explícitas (max iterations, timeout, error handling), atendendo literalmente o requisito do enunciado: *"NÃO use frameworks que escondem o loop"*.

---

## 2. Domínio: Loja Nimbus (e-commerce fictício de eletrônicos)

Eletrônicos foi escolhido por permitir faixa de preço variada (cabo de R$25 a notebook de R$5k), categorias claras e justificar políticas robustas de garantia/devolução — o que dá conteúdo coerente tanto pros CSVs quanto pro corpus de texto.

---

## 3. Dados

### 3.1 CSVs (estruturados, consultados via tools)

**`data/produtos.csv`** — catálogo (~25 linhas)
Colunas: `id, nome, categoria, marca, preco, estoque, descricao_curta`
Categorias: Periféricos, Notebooks, Smartphones, Áudio, Acessórios.

**`data/cupons.csv`** — descontos (~5 cupons)
Colunas: `codigo, tipo, valor, pedido_minimo, validade`
Tipos: `percentual` (ex: 10% off), `fixo` (ex: R$50 off), `frete_gratis`.

**`data/frete.csv`** — tabela de frete por UF (~8 linhas)
Colunas: `uf, prazo_dias, valor_base`
Regra adicional codificada na tool: pedidos acima de R$500 ganham 50% off no frete.

### 3.2 Corpus de texto (RAG, requisito do desafio)

Quatro documentos `.md` em `corpus/`:
1. `politica_trocas_devolucoes.md` — direito de arrependimento (CDC 7 dias), trocas por defeito, condições, processo
2. `formas_pagamento.md` — cartão (parcelamento até 10x), Pix (5% off), boleto, anti-fraude
3. `entrega_rastreamento.md` — modalidades (PAC/Sedex/Expressa), rastreamento, extravio, reentrega
4. `garantia_e_suporte.md` — garantia legal vs estendida, canais, prazos de retorno

### 3.3 Separação CSV vs MD (sem sobreposição)

- "Quanto custa o frete pra SP?" → CSV (`calculate_shipping`)
- "Como funciona o rastreamento?" → MD (`entrega_rastreamento.md`)
- "Tem mouse Logitech?" → CSV (`search_products`)
- "Posso devolver se não gostar?" → MD (`politica_trocas_devolucoes.md`)

CSVs têm os números; MDs têm as políticas.

---

## 4. Arquitetura

```
nimbus_ecommerce/
├── data/                       # CSVs do "banco" fictício
├── corpus/                     # 4 .md pro RAG
├── nimbus/
│   ├── llm/
│   │   ├── base.py             # interface LLMClient (chat com tools)
│   │   └── groq_client.py      # implementação Groq (llama-3.3-70b-versatile)
│   ├── rag/
│   │   ├── chunker.py          # chunking por parágrafo + overlap
│   │   ├── embeddings.py       # sentence-transformers all-MiniLM-L6-v2
│   │   └── store.py            # vector store in-memory + cosine similarity
│   ├── tools/
│   │   ├── registry.py         # schemas JSON + dispatcher
│   │   ├── catalog.py          # search_products, get_product
│   │   ├── pricing.py          # validate_coupon, calculate_shipping
│   │   ├── cart.py             # add/remove/view + estado do carrinho
│   │   └── report.py           # generate_order_report
│   ├── prompts/
│   │   └── system.md
│   ├── agent.py                # **LOOP PRÓPRIO** — peça avaliada
│   └── cli.py                  # entry point CLI
├── pedidos/                    # gerado em runtime (gitignored)
├── tests/
│   ├── test_tool_parsing.py
│   ├── test_loop_max_iter.py
│   ├── test_agent_integration.py
│   └── test_cart.py
├── pyproject.toml              # python 3.11+
├── .env.example                # GROQ_API_KEY=...
├── .gitignore
├── README.md
└── RELATO_IA.md
```

---

## 5. Loop do agente (peça central)

```python
def run_turn(user_message: str, conversation: list[dict], cart: CartState) -> str:
    conversation.append({"role": "user", "content": user_message})
    rag_context = retrieve_relevant_chunks(user_message, top_k=3)

    for iteration in range(MAX_ITERATIONS):  # = 5
        log_iteration_start(iteration)
        try:
            response = llm.chat(
                messages=build_messages(conversation, rag_context),
                tools=TOOL_SCHEMAS,
                timeout=LLM_TIMEOUT_S,  # = 30
            )
        except TimeoutError:
            return "Desculpe, tive um problema de conexão. Tente novamente."
        except LLMError as e:
            log_error(e)
            return "Erro inesperado ao consultar o modelo."

        if response.tool_calls:
            for tc in response.tool_calls:
                try:
                    result = execute_tool(tc.name, tc.arguments, cart=cart)
                except ToolError as e:
                    result = {"error": str(e)}
                conversation.append(tool_result_message(tc.id, result))
                log_tool_call(tc.name, tc.arguments, result)
            continue  # próxima iteração: o modelo processa o resultado

        conversation.append({"role": "assistant", "content": response.content})
        log_final_response(response.content)
        return response.content

    return "Não consegui resolver em tempo. Pode reformular sua pergunta?"
```

### Guardas explícitas (atendem o requisito do desafio)

| Guarda | Valor padrão | Onde |
|---|---|---|
| `MAX_ITERATIONS` | 5 | `for` do loop |
| `LLM_TIMEOUT_S` | 30 | `timeout=` do `llm.chat` |
| Tool error handling | erro estruturado de volta ao modelo | `try/except ToolError` |
| Logging por turno | stdout estruturado | `log_*` em cada passo |

### Logging
A cada turno: pergunta do usuário, mensagens enviadas ao LLM (com tool schemas omitidos), tool_calls com argumentos, resultados das tools, resposta final. Emitido em stdout.

---

## 6. Tools (8 no total)

| Tool | Função | Fonte de dados |
|---|---|---|
| `search_products(query, categoria?, max_preco?)` | Busca produtos por termo/filtros | `produtos.csv` |
| `get_product(id)` | Detalhes de 1 produto | `produtos.csv` |
| `validate_coupon(codigo, valor_pedido)` | Valida cupom e retorna desconto | `cupons.csv` |
| `calculate_shipping(uf, valor_pedido)` | Calcula frete (com regra >R$500 = 50% off) | `frete.csv` |
| `add_to_cart(produto_id, quantidade)` | Adiciona item ao carrinho | `cart_state` |
| `view_cart()` | Mostra carrinho atual | `cart_state` |
| `remove_from_cart(produto_id)` | Remove item | `cart_state` |
| `generate_order_report(uf, cupom?)` | **Gera relatório markdown final** | tudo |

> O desafio exige *pelo menos 1 tool real*. Oito é generoso, mas todas são triviais (5–15 linhas). A riqueza ajuda na demonstração e no relato.

### Tratamento de erro nas tools
Cada tool levanta `ToolError(mensagem)` em casos esperados (produto não encontrado, cupom expirado, UF inválida, estoque insuficiente). O loop captura e devolve `{"error": "..."}` ao modelo, que decide como reagir (informar o usuário, sugerir alternativa, etc.).

---

## 7. Memória multi-turno

Bônus do desafio, mas **necessário** aqui (não dá pra montar carrinho em 1 turno só):

- `conversation: list[dict]` — histórico de mensagens (user/assistant/tool), vivo durante a sessão CLI.
- `cart: CartState` — dataclass mutado pelas tools (`add_to_cart`, `remove_from_cart`).

Ambos vivem só na memória do processo. Sem persistência em disco/DB (fora de escopo do desafio).

---

## 8. RAG

- **Chunking:** por parágrafo (split em linhas em branco), com overlap de 1 parágrafo. Cada chunk carrega metadado `source` (nome do arquivo).
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (rodando local, sem API). Carregado uma vez na inicialização.
- **Store:** in-memory (lista de tuplas `(embedding, chunk, source)`).
- **Retrieval:** cosine similarity, `top_k=3`.
- **Injeção:** chunks recuperados são adicionados ao system prompt como contexto, com prefixo `[Fonte: <arquivo>]`. Quando o LLM usa essa info, é instruído a citar a fonte.

### Bônus — citação de fonte
Sistema prompt instrui: "Quando responder com base em informação institucional (políticas, FAQ, etc.), cite a fonte no formato `(fonte: nome_do_arquivo.md)`".

---

## 9. Relatório final

Quando o usuário sinaliza encerramento ("fechar pedido", "finalizar", "gerar relatório"), o LLM chama `generate_order_report(uf, cupom?)`. A tool:

1. Lê `cart_state`.
2. Busca preços atualizados em `produtos.csv`.
3. Aplica cupom (se válido).
4. Calcula frete via `calculate_shipping`.
5. Renderiza markdown e salva em `pedidos/pedido_YYYYMMDD_HHMMSS.md`.
6. Retorna pro modelo `{caminho, total, resumo}`.
7. Modelo responde ao usuário em texto natural confirmando a finalização.

### Formato do relatório

```markdown
# Pedido Loja Nimbus — 2026-04-28 14:32

## Itens
| Produto | Qtd | Preço unit. | Subtotal |
|---|---|---|---|
| Mouse Gamer Logitech G203 | 2 | R$ 159,90 | R$ 319,80 |
| Notebook Dell Inspiron 15 | 1 | R$ 4.299,00 | R$ 4.299,00 |

## Resumo
- Subtotal: R$ 4.618,80
- Cupom TECH50: -R$ 50,00
- Frete (SP, 2 dias): R$ 15,90
- **Total: R$ 4.584,70**

## Forma de pagamento sugerida
Pix (5% de desconto adicional disponível)
```

---

## 10. LLM Provider

**Padrão:** Groq, modelo `llama-3.3-70b-versatile`. Free tier generoso, suporta tool use nativo, baixa latência.

### Abstração (bônus)
Interface `LLMClient` em `nimbus/llm/base.py`:
```python
class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatResponse: ...
```

Trocar pra OpenRouter (compatível com API OpenAI) é criar `openrouter_client.py` e mudar uma linha no `cli.py`. Mesmo vale pra Anthropic, Gemini, Ollama.

---

## 11. Testes (`pytest`)

| Arquivo | Cobre |
|---|---|
| `test_tool_parsing.py` | Parsing de `tool_calls` do response do LLM (nome, argumentos, id) |
| `test_loop_max_iter.py` | Mock de LLM que sempre devolve tool_call → loop para em `MAX_ITERATIONS` |
| `test_agent_integration.py` | Mock LLMClient com sequência [tool_call → final response] → tool é executada e resposta retorna |
| `test_cart.py` (extra) | Operações de carrinho puramente no estado (add, remove, total) |

Total: 4 arquivos, ~10–15 testes. Atende o mínimo de 3 obrigatórios.

---

## 12. Bônus do desafio

| Bônus | Status | Onde |
|---|---|---|
| Abstração de LLM client | ✅ | `nimbus/llm/base.py` |
| Memória multi-turno | ✅ | necessário pro fluxo de carrinho |
| Citação da fonte no RAG | ✅ | system prompt + chunks com metadado |
| Streaming | ❌ | complica loop, ganho marginal |

---

## 13. Fora de escopo (declarado)

- Interface gráfica / web
- Autenticação, multi-tenant
- Persistência de histórico/carrinho em DB
- RAG avançado (reranking, HyDE)
- Streaming de resposta

---

## 14. Stack

- **Python:** 3.11+
- **Dependências principais:**
  - `groq` (LLM)
  - `sentence-transformers` (embeddings locais)
  - `numpy` (cosine similarity)
  - `pytest` (testes)
  - `python-dotenv` (env vars)
- **Configuração:** `.env` com `GROQ_API_KEY`. Modelo configurável via env var (`NIMBUS_MODEL`).

---

## 15. Entregáveis

- Repo público no GitHub com commits pequenos e descritivos
- `README.md` cobrindo: provider escolhido, setup, arquitetura do loop, decisões de chunking, fora de escopo
- `RELATO_IA.md` com ferramentas usadas, prompts representativos, exemplo rejeitado, trecho 100% próprio, reflexão
- 4 arquivos de teste passando (`pytest`)
- Corpus + CSVs prontos
- Tudo rodável com `pip install -e . && python -m nimbus`
