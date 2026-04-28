# Relato sobre o uso de IA — Desafio Nimbus

Este documento descreve, com transparência, como a IA foi usada na construção
deste agente. O foco é o **processo**, não o produto.

## Ferramentas e contexto

- **Claude Code (Anthropic, modelo Opus 4.7)** — pareamento ao longo de todo o
  desafio, em formato de conversação contínua. Foi a única ferramenta de IA
  usada para escrita de código.
- **Plugin "superpowers"** instalado no Claude Code, que adiciona um conjunto
  de _skills_ (workflows guiados) que estruturaram a entrega:
  - `superpowers:brainstorming` — diálogo guiado para clarificar requisitos e
    explorar 2-3 abordagens antes de comprometer com qualquer design.
  - `superpowers:writing-plans` — converte o spec aprovado em um plano de
    implementação task-a-task, em formato TDD (teste falhando → implementação
    → verde → commit).
  - `superpowers:subagent-driven-development` — executa o plano dispatchando
    um subagente por chunk, com revisão entre tarefas.
  - `superpowers:code-reviewer` — revisão final independente do código antes
    da entrega.

Nenhuma outra ferramenta (Cursor, Copilot, ChatGPT) foi usada. Decisões de
arquitetura e validação ponta-a-ponta foram minhas.

## Fluxo de trabalho

1. **Brainstorming guiado.** Colei o enunciado e o skill `brainstorming` me
   conduziu por uma sequência de perguntas focadas: provider de LLM, domínio
   fictício, estrutura de dados, escopo dos bônus. Cheguei ao recorte
   ("e-commerce de eletrônicos com 9 tools e 4 docs institucionais") por
   eliminação consciente, não por palpite do modelo.
2. **Bandeira de risco antes de começar.** Quando mencionei usar **Agno** (que
   tem uma UI de teste agradável, AgentOS), a IA imediatamente apontou que
   Agno gerencia o loop internamente — exatamente o que o enunciado proíbe.
   Recomendou três caminhos (loop próprio + Agno como camada extra, só Agno,
   só loop próprio) e eu escolhi a opção mais conservadora: loop próprio puro.
3. **Spec antes de código.** O design ficou em
   `docs/superpowers/specs/2026-04-28-ecommerce-agent-design.md` e passou por
   uma rodada de revisão minha antes de virar plano.
4. **Plano antes de execução.** O plano (em
   `docs/superpowers/plans/2026-04-28-ecommerce-agent-plan.md`) tem 17 tarefas
   TDD-driven, cada uma com código completo dos testes e da implementação.
5. **Execução via subagentes.** O `subagent-driven-development` dispatch um
   subagente por chunk de tarefas (skeleton, tools, RAG, agent loop, CLI,
   docs). Cada commit do histórico foi gerado nesse fluxo.
6. **Iteração guiada por logs reais.** A versão inicial passou na review, mas
   uma sessão real com Gemini 2.5 Flash via OpenRouter expôs problemas
   concretos (RAG retornando título-só, modelo inventando cupom "PIX5",
   `max_preco=0` filtrando tudo). Cada um virou um commit de fix, com testes.

O ponto não é que a IA "fez sozinha" — é que houve uma cadeia de
**decisões + revisões + iteração** que a moldou.

## Prompts representativos (com contexto)

Selecionei quatro momentos da conversa em que o **prompt foi o que decidiu**
o resultado, não o modelo:

### 1. Bandeira de risco antes de aceitar a sugestão

> "Acredito que vou usar a api do open router o que precisa trocar no projeto
> para isso?"

Aqui não pedi mudança de provider — pedi o **diff conceitual**. A resposta
listou exatamente o que precisava mudar (1 arquivo novo, 1 dispatcher na CLI,
3 linhas no `.env.example`). Permitiu que eu avaliasse esforço antes de
mergulhar.

### 2. Pergunta que virou refactor importante

> "Esse exemplo do rag ficou ruim pq pergunta se tem produto da logitech e
> recupera um rag texto nada haver. Alem disso todo turno ta injetando o rag ou só quando o
> modelo chama?"

Era uma pergunta diagnóstica, não uma instrução. A resposta confirmou que era
**injeção automática** todo turno e propôs converter em tool (`search_policies`).
Esse refactor mudou o design fundamentalmente — RAG passou de "contexto
empurrado" para "ferramenta puxada pelo modelo". Sem essa pergunta, teria
ficado com a versão inferior.

### 3. Pedido de análise dirigida por dados

> "Analise os logs da conversa e ve se tem q melhorar algo no prompt/agent"
> [+ log completo de uma sessão]

Em vez de pedir refinamentos abstratos, dei o log real e pedi análise. A IA
identificou 4 problemas concretos (chunking ruim, `max_preco=0`, hallucination
do cupom PIX5, `view_cart` redundante). Cada um virou commit de fix com teste.

### 4. Restrição de simplicidade

> "Quero que o rag recupere o documento inteiro nao precisa separar em chunks
> pq é muito pequeno"

Direto, opinativo, derruba uma decisão de design anterior (chunking por
parágrafo com overlap). Forçou a simplificação certa: 4 docs pequenos = 4
chunks. Resultou em código mais simples e busca melhor.

## Sugestões da IA que **rejeitei ou modifiquei**

- **RAG injetado em todo turno.** Era o design inicial proposto pela IA no
  spec original. Após a sessão real mostrar contexto irrelevante em pergunta
  de catálogo, pedi a conversão para tool — refactor significativo.
- **Chunking por parágrafo com overlap.** Padrão "elegante" que a IA propôs
  no spec. Rejeitei após ver no log real que retornava títulos vazios. Trocado
  por whole-document.
- **Cupom "PIX5" inventado pelo modelo Gemini.** Não era sugestão da IA, mas
  do modelo em runtime. Diagnostiquei via log e adicionei parâmetro
  `forma_pagamento` ao `generate_order_report` em vez de criar um cupom falso.
- **8 tools como peças separadas em arquivos diferentes** (`tools/search.py`,
  `tools/get_product.py`, etc.). Rejeitei: agrupei por responsabilidade
  (`catalog.py`, `pricing.py`, `cart.py`, `report.py`). Uma tool por arquivo
  é fragmentação sem benefício.
- **Persistência de carrinho/conversa em DB.** A IA sugeriu como bônus
  (SQLite leve). Mantive fora de escopo: o enunciado lista "persistência de
  histórico em banco" como fora de escopo explícito. Adicionar isso seria
  trabalho que não demonstra nada novo sobre o loop ou sobre tool use, que
  são os critérios avaliados.

## Sobre o trecho 100% próprio

Algumas tools nasceram de comportamento que **eu** desenhei, e nelas o fluxo
foi inverso do habitual: em vez de a IA gerar e eu revisar, **eu produzi a
lógica e usei a IA como revisor** ("isso faz sentido?", "estou esquecendo de
algum caso de borda?", "esse retorno está coerente com as outras tools?"). Os
exemplos mais claros:

- **`nimbus/tools/cart.py` — `add_to_cart` (linhas 20-35).** Eu desenhei a
  semântica de "se o produto já está no carrinho, soma a quantidade nova ao
  acumulado e revalida estoque contra o total" — a IA tinha proposto
  inicialmente ou sobrescrever a quantidade, ou levantar erro se já existisse.
  Pedi a versão de soma e usei a IA pra checar se estava cobrindo todos os
  casos (estoque insuficiente, quantidade ≤ 0, produto inexistente).
- **`nimbus/tools/report.py` — `forma_pagamento` como parâmetro separado.**
  Quando vi no log que o modelo Gemini estava inventando um cupom "PIX5" pra
  aplicar a regra dos 5% de desconto via Pix, projetei a solução: separar
  cupom (lookup em tabela) de forma de pagamento (regra automática), com
  desconto Pix calculado sobre `subtotal - desconto_cupom` pra não
  sobrepor com cupons percentuais. A IA refinou detalhes (formatação BRL,
  ordem das linhas no markdown final).
- **`nimbus/prompts/system.md`** — reescrito por mim várias vezes em resposta
  a falhas observadas em sessão real ("aja, não anuncie", "PIX é
  forma_pagamento, não cupom", "não chame view_cart após add_to_cart"). A IA
  gerou frases, mas o conteúdo de cada regra veio do que **eu** vi quebrar.

Além das tools, o que **é meu sem ressalva**:

- Escolha de domínio (e-commerce de eletrônicos, pivot meu) e cada decisão de
  escopo (sem persistência em DB, sem Agno, RAG whole-document, janela de 7
  turnos).
- Cada **fix guiado por log** veio da minha leitura dos logs reais, não de
  inferência da IA — sem eu rodar e ler, ela não detectaria.

## Reflexão (5 linhas)

A IA acelerou principalmente: o boilerplate (testes pytest, schemas JSON,
glue code), a exploração de alternativas no brainstorming, e a escrita das
políticas fictícias do corpus (criatividade controlada). Atrapalhou em duas
frentes recorrentes: tendência a sobre-modularizar (uma função por arquivo,
abstrações pré-maturas) e a fazer suposições otimistas sobre comportamento do
LLM em runtime — só uma sessão real com tokens reais expôs que Gemini ignora
tools e inventa cupons. A regra que segui foi: usar IA pra explorar e gerar
primeira versão, mas testar com dados reais antes de declarar pronto. Sem o
loop "rode → leia o log → conserte", o produto seria pior.
