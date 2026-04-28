# Relato do uso de IA — Desafio Nimbus

## Ferramentas usadas

- **Claude Code (Anthropic)** — pareamento ao longo de todo o desafio: brainstorming do escopo, design, escrita do plano de implementação, geração inicial dos blocos de código.
- **GitHub Copilot** — autocomplete pontual em IDE (não usado em decisões estruturais).

## Onde a IA atuou

- Brainstorming do domínio fictício e validação do escopo contra o enunciado (incluindo o ponto crítico do "loop sem framework" — a IA propôs Agno e eu rejeitei).
- Estruturação dos arquivos e fronteiras entre módulos.
- Geração dos textos do corpus institucional (políticas, FAQ).
- Esqueleto dos testes pytest.

## Onde **eu** atuei sem IA

- Decisão de domínio (e-commerce de eletrônicos), escolha de provider (Groq), escopo dos bônus.
- Revisão linha-a-linha de cada bloco gerado, ajuste de nomes, simplificações.
- Validação manual do fluxo conversacional ponta a ponta (REPL).

## 2-4 prompts representativos

**1. Levantamento de bandeira de risco:**
> "Quero usar o Agno + AgentOS pra esse desafio."
>
> Resposta da IA (resumida): apontou que o enunciado proíbe explicitamente frameworks que escondem o loop, listou 3 alternativas (loop próprio + Agno como camada extra, só Agno aceitando o risco, só loop próprio) e recomendou loop próprio. Decidi pelo loop próprio puro.

**2. Estruturação do corpus vs CSVs:**
> "Como dividir o que vai pra CSV (consultado via tools) e o que vai pra .md (consultado via RAG) sem sobreposição?"
>
> Resposta gerou a regra "CSV tem números, MD tem políticas" que adotei diretamente — passou a separação clara: `frete.csv` calcula valor/prazo, `entrega_rastreamento.md` explica como rastrear/o que fazer em extravio.

**3. Design do loop:**
> "Mostra o pseudocódigo do loop com max_iterations, timeout e error handling, sem usar frameworks."
>
> A primeira versão tinha tratamento de erro genérico demais (`except Exception`); refinei pra distinguir `ToolError` (esperado, vai pro modelo) de `Exception` (inesperado, loga + erro genérico ao usuário).

## Algo que rejeitei / modifiquei

A IA sugeriu inicialmente **8 tools como peças separadas em arquivos diferentes** (`tools/search.py`, `tools/get_product.py`, `tools/add_to_cart.py`, etc.), uma tool por arquivo. Rejeitei: agrupei por responsabilidade (`catalog.py`, `pricing.py`, `cart.py`, `report.py`), porque uma tool por arquivo gera fragmentação sem benefício — funções de catálogo compartilham o `load_products` e mantê-las juntas reduz indireção. A abstração de "uma tool por arquivo" é pseudo-modularidade.

## Trecho 100% meu (sem IA)

`nimbus/tools/cart.py:30-46` — a função `add_to_cart` com a lógica de "se já existe, soma à quantidade e revalida estoque". Escrevi à mão porque a IA tinha proposto ou (a) sobrescrever a quantidade, ou (b) lançar erro se já existe — ambos comportamentos errados pra UX de carrinho.

## Reflexão

A IA acelerou principalmente: brainstorming inicial (exploração de alternativas que eu não pensaria), boilerplate dos testes pytest (estrutura repetitiva) e geração dos textos do corpus institucional (criatividade controlada). Atrapalhou em dois pontos: tendência a sobre-modularizar arquivos (uma função por arquivo, fragmentação artificial) e em alguns testes começou a mockar o que não precisava ser mockado. A regra que segui foi: usar IA pra explorar e gerar primeira versão, mas revisar tudo com olhar de "isso me ajuda a manter o código simples ou está adicionando peso?".
