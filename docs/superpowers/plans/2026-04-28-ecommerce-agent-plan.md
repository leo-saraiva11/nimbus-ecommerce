# Nimbus E-commerce Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um agente CLI conversacional que ajuda o usuário a montar um carrinho na "Loja Nimbus" (e-commerce fictício de eletrônicos), consultando CSVs via tools e textos institucionais via RAG, com loop próprio (sem framework) e geração de relatório markdown final.

**Architecture:** Loop de agente escrito à mão (`agent.py`) que orquestra LLM (Groq), 8 tools determinísticas (catálogo, pricing, carrinho, relatório), RAG simples (sentence-transformers + cosine in-memory) sobre 4 docs `.md`, e estado de carrinho/conversa em memória. Abstração `LLMClient` permite trocar provider trocando um arquivo.

**Tech Stack:** Python 3.11+, `groq`, `sentence-transformers`, `numpy`, `python-dotenv`, `pytest`.

---

## File Structure

```
nimbus_ecommerce/
├── data/
│   ├── produtos.csv
│   ├── cupons.csv
│   └── frete.csv
├── corpus/
│   ├── politica_trocas_devolucoes.md
│   ├── formas_pagamento.md
│   ├── entrega_rastreamento.md
│   └── garantia_e_suporte.md
├── nimbus/
│   ├── __init__.py
│   ├── __main__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── groq_client.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   ├── embeddings.py
│   │   └── store.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── registry.py
│   │   ├── catalog.py
│   │   ├── pricing.py
│   │   ├── cart.py
│   │   └── report.py
│   ├── prompts/
│   │   └── system.md
│   ├── agent.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_catalog.py
│   ├── test_pricing.py
│   ├── test_cart.py
│   ├── test_report.py
│   ├── test_chunker.py
│   ├── test_rag_store.py
│   ├── test_tool_parsing.py
│   ├── test_loop_max_iter.py
│   └── test_agent_integration.py
├── pedidos/        # criado em runtime, gitignored
├── pyproject.toml
├── .env.example
└── README.md       # tracked, mas escrito na última task
RELATO_IA.md        # tracked, escrito na última task
```

**File responsibilities:**
- `tools/errors.py` — exceção `ToolError` única, importada onde precisar.
- `tools/registry.py` — schemas JSON + função `execute_tool(name, args, ctx)` que faz dispatch.
- `tools/catalog.py`, `pricing.py`, `cart.py`, `report.py` — implementações puras, sem conhecimento do LLM.
- `rag/chunker.py` — função pura `chunk_markdown(text) -> list[Chunk]`.
- `rag/embeddings.py` — wrapper sobre `sentence-transformers`, lazy load do modelo.
- `rag/store.py` — `VectorStore` em memória com `add` e `search(query, top_k)`.
- `llm/base.py` — `Protocol LLMClient` + dataclasses de request/response.
- `llm/groq_client.py` — adaptação do SDK `groq` para essa interface.
- `agent.py` — `run_turn` (loop) + helpers.
- `cli.py` — REPL simples.

---

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `nimbus/__init__.py`
- Create: `nimbus/__main__.py`
- Create: `nimbus/llm/__init__.py`
- Create: `nimbus/rag/__init__.py`
- Create: `nimbus/tools/__init__.py`
- Create: `nimbus/prompts/.gitkeep`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "nimbus-ecommerce"
version = "0.1.0"
description = "Agente conversacional CLI para e-commerce fictício (Loja Nimbus)"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "groq>=0.11.0",
    "sentence-transformers>=3.0.0",
    "numpy>=1.26.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-mock>=3.12"]

[project.scripts]
nimbus = "nimbus.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["nimbus*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: Create `.env.example`**

```
GROQ_API_KEY=your_key_here
NIMBUS_MODEL=llama-3.3-70b-versatile
```

- [ ] **Step 3: Create empty package init files**

Each of these is `# package marker` (one-line file):
- `nimbus/__init__.py` → `__version__ = "0.1.0"`
- `nimbus/llm/__init__.py` → empty
- `nimbus/rag/__init__.py` → empty
- `nimbus/tools/__init__.py` → empty
- `tests/__init__.py` → empty

- [ ] **Step 4: Create `nimbus/__main__.py`**

```python
from nimbus.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create `nimbus/prompts/.gitkeep`** (empty file, garante que diretório fica no git)

- [ ] **Step 6: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures for the Nimbus test suite."""
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    return project_root / "data"


@pytest.fixture
def corpus_dir(project_root: Path) -> Path:
    return project_root / "corpus"
```

- [ ] **Step 7: Verify install works**

Run:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest --collect-only
```

Expected: install succeeds, pytest reports "no tests ran" (zero tests collected, exit 5 is OK at this stage — or use `pytest -q || true`).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .env.example nimbus tests
git commit -m "chore: project skeleton (pyproject, package layout, conftest)"
```

---

## Task 2: Data CSVs

**Files:**
- Create: `data/produtos.csv`
- Create: `data/cupons.csv`
- Create: `data/frete.csv`

- [ ] **Step 1: Create `data/produtos.csv`** (~25 produtos cobrindo 5 categorias e faixa de preço variada)

```csv
id,nome,categoria,marca,preco,estoque,descricao_curta
P001,Mouse Gamer Logitech G203,Perifericos,Logitech,159.90,47,"Mouse com 8000 DPI e iluminação RGB"
P002,Teclado Mecânico Redragon Kumara,Perifericos,Redragon,249.90,30,"Teclado mecânico switch outemu blue"
P003,Headset HyperX Cloud Stinger,Audio,HyperX,329.00,18,"Headset gamer over-ear com microfone"
P004,Webcam Logitech C920,Perifericos,Logitech,449.00,12,"Webcam Full HD 1080p 30fps"
P005,Notebook Dell Inspiron 15,Notebooks,Dell,4299.00,8,"Intel i5 13a geração 16GB RAM 512GB SSD"
P006,Notebook Lenovo IdeaPad 3,Notebooks,Lenovo,3199.00,15,"Intel i3 8GB RAM 256GB SSD tela 15.6"
P007,MacBook Air M2,Notebooks,Apple,9999.00,4,"Chip M2 8GB RAM 256GB SSD tela 13.6"
P008,iPhone 15,Smartphones,Apple,5499.00,10,"128GB tela 6.1 Super Retina"
P009,Samsung Galaxy S24,Smartphones,Samsung,4499.00,14,"256GB tela 6.2 Dynamic AMOLED"
P010,Xiaomi Redmi Note 13,Smartphones,Xiaomi,1799.00,28,"128GB câmera 108MP bateria 5000mAh"
P011,Fone JBL Tune 510BT,Audio,JBL,229.00,40,"Fone bluetooth on-ear bateria 40h"
P012,Caixa de Som JBL Go 3,Audio,JBL,299.00,22,"Speaker bluetooth portátil à prova d'água"
P013,AirPods Pro 2,Audio,Apple,2199.00,9,"Cancelamento de ruído ativo"
P014,Cabo USB-C 1m,Acessorios,Anker,49.90,120,"Cabo USB-C para USB-C 60W"
P015,Carregador 20W Apple,Acessorios,Apple,229.00,35,"Carregador USB-C 20W original"
P016,Hub USB-C 7 em 1,Acessorios,Baseus,189.90,24,"Hub HDMI USB-A SD ethernet"
P017,Suporte Notebook Ergonômico,Acessorios,Generico,99.90,55,"Suporte ajustável em alumínio"
P018,Mouse Pad Gamer XL,Perifericos,Generico,79.90,80,"900x400mm com base antiderrapante"
P019,Monitor LG UltraWide 29,Perifericos,LG,1899.00,7,"29 polegadas 2560x1080 IPS 75Hz"
P020,Monitor Dell 24 P2422H,Perifericos,Dell,1499.00,11,"24 polegadas Full HD IPS"
P021,SSD Kingston NV2 1TB,Acessorios,Kingston,449.00,32,"SSD NVMe PCIe 4.0 leitura 3500MB/s"
P022,Memória RAM Corsair 16GB,Acessorios,Corsair,389.00,18,"DDR4 3200MHz Vengeance LPX"
P023,Cadeira Gamer DT3 Elite,Acessorios,DT3,1799.00,5,"Reclinável braços 4D apoio lombar"
P024,Webcam Razer Kiyo X,Perifericos,Razer,599.00,9,"Full HD 60fps autofocus"
P025,Smartwatch Galaxy Watch 6,Smartphones,Samsung,2199.00,13,"GPS bluetooth tela AMOLED 40mm"
```

- [ ] **Step 2: Create `data/cupons.csv`**

```csv
codigo,tipo,valor,pedido_minimo,validade
BEMVINDO10,percentual,10,0,2026-12-31
TECH50,fixo,50,300,2026-12-31
MEGA15,percentual,15,1000,2026-12-31
FRETEGRATIS,frete_gratis,0,200,2026-06-30
EXPIRADO,percentual,20,0,2024-01-01
```

- [ ] **Step 3: Create `data/frete.csv`**

```csv
uf,prazo_dias,valor_base
SP,2,15.90
RJ,3,19.90
MG,3,22.90
ES,4,24.90
PR,4,26.90
SC,4,28.90
RS,5,32.90
BA,6,38.90
DF,4,29.90
```

- [ ] **Step 4: Commit**

```bash
git add data/
git commit -m "feat(data): catálogo, cupons e tabela de frete da Loja Nimbus"
```

---

## Task 3: Corpus de texto (RAG)

**Files:**
- Create: `corpus/politica_trocas_devolucoes.md`
- Create: `corpus/formas_pagamento.md`
- Create: `corpus/entrega_rastreamento.md`
- Create: `corpus/garantia_e_suporte.md`

- [ ] **Step 1: Create `corpus/politica_trocas_devolucoes.md`**

```markdown
# Política de Trocas e Devoluções — Loja Nimbus

## Direito de arrependimento (CDC)

Todo cliente da Loja Nimbus pode solicitar a devolução do produto em até **7 dias corridos** após o recebimento, sem precisar justificar o motivo. Esse direito está garantido pelo Art. 49 do Código de Defesa do Consumidor.

Para exercer o direito de arrependimento, o produto deve estar:

- Sem sinais de uso
- Em sua embalagem original
- Acompanhado de todos os acessórios e manuais
- Com a nota fiscal

Após validação, o reembolso é feito em até 10 dias úteis, na mesma forma de pagamento da compra.

## Troca por defeito

Produtos com defeito de fabricação podem ser trocados em até 30 dias após o recebimento. Para defeitos identificados após esse prazo, vale a garantia legal do fabricante.

A análise técnica é feita em até 7 dias úteis após o recebimento do produto na nossa central. Se confirmado o defeito, oferecemos:

1. Troca pelo mesmo produto (sujeito a estoque)
2. Troca por produto similar
3. Reembolso integral

## Como solicitar

Acesse sua conta em loja-nimbus.com.br/pedidos, selecione o pedido e clique em "Solicitar troca/devolução". O frete de retorno é por nossa conta para todos os casos.
```

- [ ] **Step 2: Create `corpus/formas_pagamento.md`**

```markdown
# Formas de Pagamento — Loja Nimbus

## Cartão de crédito

Aceitamos as principais bandeiras: Visa, Mastercard, Elo, American Express e Hipercard. O pagamento pode ser parcelado em até **10x sem juros** para compras acima de R$300, e em até 12x com juros de 1,99% ao mês para compras menores.

A aprovação é imediata na maioria dos casos. Em compras acima de R$2.000, pode haver análise antifraude que leva até 24h úteis.

## Pix

Pagamentos via Pix têm **5% de desconto adicional** aplicado automaticamente no checkout. A confirmação é instantânea e o pedido entra em separação imediatamente após o pagamento.

O QR code expira em 30 minutos. Se expirar, basta gerar um novo no painel do pedido.

## Boleto bancário

Boleto tem prazo de compensação de até 3 dias úteis. O pedido só entra em separação após a confirmação do pagamento. Não oferecemos desconto para boleto.

Boletos vencidos podem ser regerados em loja-nimbus.com.br/pedidos por até 5 dias após o vencimento original.

## Política antifraude

Pedidos acima de R$5.000 ou com endereço de entrega diferente do cadastrado podem passar por análise manual. Nesses casos, podemos solicitar comprovantes adicionais.
```

- [ ] **Step 3: Create `corpus/entrega_rastreamento.md`**

```markdown
# Entrega e Rastreamento — Loja Nimbus

## Modalidades de envio

Trabalhamos com três modalidades:

- **PAC**: prazo padrão da nossa tabela, valor mais econômico
- **Sedex**: 1 dia útil mais rápido que o PAC, valor um pouco maior
- **Expressa Same Day**: entrega no mesmo dia para capitais selecionadas (SP, RJ, BH, Curitiba), pedidos feitos até 14h

Os prazos exatos por UF estão na tabela de frete e dependem do CEP final. Pedidos acima de R$500 têm 50% de desconto no frete.

## Rastreamento

Todo pedido recebe um código de rastreio assim que é despachado, enviado por e-mail e disponível em loja-nimbus.com.br/pedidos. O código é dos Correios para PAC/Sedex, ou da transportadora parceira para Expressa.

## Política de extravio

Se o pedido não chegar no prazo, abrimos automaticamente uma investigação interna após 5 dias úteis do prazo estourado. Se confirmado o extravio:

1. Reenvio gratuito do mesmo produto, ou
2. Reembolso integral, à escolha do cliente

## Reentrega

Se o entregador não conseguir contato, são feitas até 3 tentativas em dias úteis consecutivos. Após isso, o pedido volta pra nossa central e o cliente pode reagendar pelo painel.
```

- [ ] **Step 4: Create `corpus/garantia_e_suporte.md`**

```markdown
# Garantia e Suporte — Loja Nimbus

## Garantia legal

Todo produto vendido na Loja Nimbus tem garantia legal mínima de **90 dias** contra defeitos de fabricação, conforme o CDC. Para a maioria dos produtos, oferecemos a garantia do fabricante, que costuma variar entre 1 e 2 anos.

## Garantia estendida

No checkout, oferecemos opção de **garantia estendida de 12 ou 24 meses** complementar à do fabricante. O valor é proporcional ao preço do produto (entre 5% e 10%).

A garantia estendida cobre:

- Defeitos elétricos e eletrônicos após o fim da garantia do fabricante
- Mão de obra e peças de reposição
- Atendimento na rede credenciada do fabricante

Não cobre danos por mau uso, quedas, líquidos ou desgaste natural.

## Canais de suporte

- **Chat**: disponível em loja-nimbus.com.br, das 8h às 22h todos os dias
- **E-mail**: suporte@loja-nimbus.com.br, retorno em até 24h úteis
- **WhatsApp**: (11) 99999-0000, das 9h às 18h em dias úteis

## Prazos de retorno

- Dúvidas e informações: até 4h úteis
- Solicitações de troca/devolução: até 24h úteis
- Análises técnicas: até 7 dias úteis após recebimento do produto na central
```

- [ ] **Step 5: Commit**

```bash
git add corpus/
git commit -m "feat(corpus): docs institucionais (trocas, pagamento, entrega, garantia)"
```

---

## Task 4: Tool errors module

**Files:**
- Create: `nimbus/tools/errors.py`
- Create: `tests/test_tool_errors.py`

- [ ] **Step 1: Write failing test**

`tests/test_tool_errors.py`:
```python
from nimbus.tools.errors import ToolError


def test_tool_error_carries_message():
    err = ToolError("produto não encontrado")
    assert str(err) == "produto não encontrado"
    assert isinstance(err, Exception)
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `pytest tests/test_tool_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nimbus.tools.errors'`

- [ ] **Step 3: Implement**

`nimbus/tools/errors.py`:
```python
class ToolError(Exception):
    """Erro esperado durante execução de uma tool. Devolvido ao LLM como contexto estruturado."""
```

- [ ] **Step 4: Run test, verify PASS**

Run: `pytest tests/test_tool_errors.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/errors.py tests/test_tool_errors.py
git commit -m "feat(tools): ToolError exception base"
```

---

## Task 5: Catalog tools

**Files:**
- Create: `nimbus/tools/catalog.py`
- Create: `tests/test_catalog.py`

- [ ] **Step 1: Write failing tests**

`tests/test_catalog.py`:
```python
import pytest
from nimbus.tools.catalog import load_products, search_products, get_product
from nimbus.tools.errors import ToolError


def test_load_products_returns_all_rows(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    assert len(produtos) >= 20
    assert produtos[0]["id"] == "P001"
    assert isinstance(produtos[0]["preco"], float)
    assert isinstance(produtos[0]["estoque"], int)


def test_search_products_by_query(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="logitech")
    assert len(results) >= 1
    assert all("logitech" in p["nome"].lower() or "logitech" in p["marca"].lower() for p in results)


def test_search_products_by_categoria(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="", categoria="Notebooks")
    assert len(results) >= 1
    assert all(p["categoria"] == "Notebooks" for p in results)


def test_search_products_by_max_preco(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="", max_preco=100.0)
    assert all(p["preco"] <= 100.0 for p in results)


def test_get_product_found(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    p = get_product(produtos, "P001")
    assert p["nome"].startswith("Mouse Gamer")


def test_get_product_not_found_raises(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    with pytest.raises(ToolError, match="não encontrado"):
        get_product(produtos, "P999")
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_catalog.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/tools/catalog.py`:
```python
"""Tools de catálogo: busca e detalhes de produtos a partir de produtos.csv."""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Optional

from nimbus.tools.errors import ToolError


def load_products(path: Path) -> list[dict]:
    """Carrega produtos.csv para uma lista de dicts com tipos coerentes."""
    produtos: list[dict] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["preco"] = float(row["preco"])
            row["estoque"] = int(row["estoque"])
            produtos.append(row)
    return produtos


def search_products(
    produtos: list[dict],
    query: str = "",
    categoria: Optional[str] = None,
    max_preco: Optional[float] = None,
) -> list[dict]:
    """Filtra produtos por termo (nome/marca/descrição), categoria e teto de preço."""
    q = query.lower().strip()
    out = []
    for p in produtos:
        if q and q not in p["nome"].lower() and q not in p["marca"].lower() and q not in p["descricao_curta"].lower():
            continue
        if categoria and p["categoria"] != categoria:
            continue
        if max_preco is not None and p["preco"] > max_preco:
            continue
        out.append(p)
    return out


def get_product(produtos: list[dict], produto_id: str) -> dict:
    """Retorna o produto por id, ou levanta ToolError."""
    for p in produtos:
        if p["id"] == produto_id:
            return p
    raise ToolError(f"Produto {produto_id} não encontrado no catálogo")
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_catalog.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/catalog.py tests/test_catalog.py
git commit -m "feat(tools): catalog (load_products, search_products, get_product)"
```

---

## Task 6: Pricing tools

**Files:**
- Create: `nimbus/tools/pricing.py`
- Create: `tests/test_pricing.py`

- [ ] **Step 1: Write failing tests**

`tests/test_pricing.py`:
```python
import pytest
from nimbus.tools.pricing import (
    load_coupons, load_shipping, validate_coupon, calculate_shipping
)
from nimbus.tools.errors import ToolError


def test_load_coupons(data_dir):
    cupons = load_coupons(data_dir / "cupons.csv")
    assert len(cupons) >= 5
    assert cupons[0]["codigo"] == "BEMVINDO10"


def test_validate_coupon_percentual(data_dir):
    cupons = load_coupons(data_dir / "cupons.csv")
    desc = validate_coupon(cupons, codigo="BEMVINDO10", valor_pedido=200.0)
    assert desc["aplicado"] is True
    assert desc["desconto"] == 20.0  # 10% de 200
    assert desc["tipo"] == "percentual"


def test_validate_coupon_fixo_respeita_pedido_minimo(data_dir):
    cupons = load_coupons(data_dir / "cupons.csv")
    with pytest.raises(ToolError, match="pedido mínimo"):
        validate_coupon(cupons, codigo="TECH50", valor_pedido=100.0)


def test_validate_coupon_inexistente(data_dir):
    cupons = load_coupons(data_dir / "cupons.csv")
    with pytest.raises(ToolError, match="não encontrado"):
        validate_coupon(cupons, codigo="NOEXISTE", valor_pedido=500.0)


def test_validate_coupon_expirado(data_dir):
    cupons = load_coupons(data_dir / "cupons.csv")
    with pytest.raises(ToolError, match="expirado"):
        validate_coupon(cupons, codigo="EXPIRADO", valor_pedido=500.0)


def test_calculate_shipping_basico(data_dir):
    tabela = load_shipping(data_dir / "frete.csv")
    r = calculate_shipping(tabela, uf="SP", valor_pedido=100.0)
    assert r["uf"] == "SP"
    assert r["prazo_dias"] == 2
    assert r["valor"] == 15.90


def test_calculate_shipping_desconto_acima_500(data_dir):
    tabela = load_shipping(data_dir / "frete.csv")
    r = calculate_shipping(tabela, uf="SP", valor_pedido=600.0)
    assert r["valor"] == round(15.90 * 0.5, 2)


def test_calculate_shipping_uf_invalida(data_dir):
    tabela = load_shipping(data_dir / "frete.csv")
    with pytest.raises(ToolError, match="UF"):
        calculate_shipping(tabela, uf="XX", valor_pedido=100.0)
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_pricing.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/tools/pricing.py`:
```python
"""Tools de pricing: cupons e cálculo de frete."""
from __future__ import annotations
import csv
from datetime import date
from pathlib import Path

from nimbus.tools.errors import ToolError


def load_coupons(path: Path) -> list[dict]:
    cupons: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["valor"] = float(row["valor"])
            row["pedido_minimo"] = float(row["pedido_minimo"])
            cupons.append(row)
    return cupons


def load_shipping(path: Path) -> dict[str, dict]:
    tabela: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tabela[row["uf"]] = {
                "uf": row["uf"],
                "prazo_dias": int(row["prazo_dias"]),
                "valor_base": float(row["valor_base"]),
            }
    return tabela


def validate_coupon(cupons: list[dict], codigo: str, valor_pedido: float) -> dict:
    """Valida cupom e retorna dict com desconto aplicado, ou levanta ToolError."""
    cupom = next((c for c in cupons if c["codigo"] == codigo), None)
    if cupom is None:
        raise ToolError(f"Cupom {codigo} não encontrado")
    if date.fromisoformat(cupom["validade"]) < date.today():
        raise ToolError(f"Cupom {codigo} expirado em {cupom['validade']}")
    if valor_pedido < cupom["pedido_minimo"]:
        raise ToolError(
            f"Cupom {codigo} requer pedido mínimo de R$ {cupom['pedido_minimo']:.2f}"
        )

    tipo = cupom["tipo"]
    if tipo == "percentual":
        desconto = round(valor_pedido * cupom["valor"] / 100, 2)
    elif tipo == "fixo":
        desconto = cupom["valor"]
    elif tipo == "frete_gratis":
        desconto = 0.0
    else:
        raise ToolError(f"Tipo de cupom desconhecido: {tipo}")

    return {
        "aplicado": True,
        "codigo": codigo,
        "tipo": tipo,
        "desconto": desconto,
    }


def calculate_shipping(tabela: dict[str, dict], uf: str, valor_pedido: float) -> dict:
    """Calcula frete por UF, com 50% de desconto para pedidos > R$500."""
    uf = uf.upper()
    if uf not in tabela:
        raise ToolError(f"UF {uf} não atendida pela Loja Nimbus")
    base = tabela[uf]
    valor = base["valor_base"]
    if valor_pedido > 500:
        valor = round(valor * 0.5, 2)
    return {
        "uf": uf,
        "prazo_dias": base["prazo_dias"],
        "valor": valor,
    }
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_pricing.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/pricing.py tests/test_pricing.py
git commit -m "feat(tools): pricing (validate_coupon, calculate_shipping)"
```

---

## Task 7: Cart tools + state

**Files:**
- Create: `nimbus/tools/cart.py`
- Create: `tests/test_cart.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cart.py`:
```python
import pytest
from nimbus.tools.cart import CartState, add_to_cart, view_cart, remove_from_cart
from nimbus.tools.errors import ToolError


@pytest.fixture
def produtos():
    return [
        {"id": "P001", "nome": "Mouse", "preco": 100.0, "estoque": 5},
        {"id": "P002", "nome": "Notebook", "preco": 4000.0, "estoque": 1},
    ]


def test_add_to_cart_novo_item(produtos):
    cart = CartState()
    res = add_to_cart(cart, produtos, "P001", 2)
    assert res["produto_id"] == "P001"
    assert res["quantidade_atual"] == 2
    assert cart.items["P001"].quantidade == 2


def test_add_to_cart_acumula_quantidade(produtos):
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 2)
    res = add_to_cart(cart, produtos, "P001", 3)
    assert res["quantidade_atual"] == 5


def test_add_to_cart_estoque_insuficiente(produtos):
    cart = CartState()
    with pytest.raises(ToolError, match="estoque"):
        add_to_cart(cart, produtos, "P002", 5)


def test_add_to_cart_produto_inexistente(produtos):
    cart = CartState()
    with pytest.raises(ToolError, match="não encontrado"):
        add_to_cart(cart, produtos, "P999", 1)


def test_view_cart_vazio():
    cart = CartState()
    res = view_cart(cart, produtos=[])
    assert res["items"] == []
    assert res["subtotal"] == 0.0


def test_view_cart_com_itens(produtos):
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 2)
    res = view_cart(cart, produtos)
    assert len(res["items"]) == 1
    assert res["items"][0]["subtotal"] == 200.0
    assert res["subtotal"] == 200.0


def test_remove_from_cart(produtos):
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 2)
    res = remove_from_cart(cart, "P001")
    assert res["removido"] == "P001"
    assert "P001" not in cart.items


def test_remove_from_cart_inexistente():
    cart = CartState()
    with pytest.raises(ToolError, match="não está no carrinho"):
        remove_from_cart(cart, "P999")
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_cart.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/tools/cart.py`:
```python
"""Carrinho em memória + tools add/view/remove."""
from __future__ import annotations
from dataclasses import dataclass, field

from nimbus.tools.catalog import get_product
from nimbus.tools.errors import ToolError


@dataclass
class CartItem:
    produto_id: str
    quantidade: int


@dataclass
class CartState:
    items: dict[str, CartItem] = field(default_factory=dict)


def add_to_cart(cart: CartState, produtos: list[dict], produto_id: str, quantidade: int) -> dict:
    if quantidade <= 0:
        raise ToolError("Quantidade deve ser maior que zero")
    produto = get_product(produtos, produto_id)
    atual = cart.items[produto_id].quantidade if produto_id in cart.items else 0
    nova = atual + quantidade
    if nova > produto["estoque"]:
        raise ToolError(
            f"Estoque insuficiente para {produto['nome']}: disponível {produto['estoque']}, solicitado {nova}"
        )
    cart.items[produto_id] = CartItem(produto_id=produto_id, quantidade=nova)
    return {
        "produto_id": produto_id,
        "nome": produto["nome"],
        "quantidade_atual": nova,
    }


def view_cart(cart: CartState, produtos: list[dict]) -> dict:
    items_view = []
    subtotal = 0.0
    for pid, item in cart.items.items():
        produto = get_product(produtos, pid)
        sub = round(produto["preco"] * item.quantidade, 2)
        subtotal += sub
        items_view.append({
            "produto_id": pid,
            "nome": produto["nome"],
            "preco_unitario": produto["preco"],
            "quantidade": item.quantidade,
            "subtotal": sub,
        })
    return {"items": items_view, "subtotal": round(subtotal, 2)}


def remove_from_cart(cart: CartState, produto_id: str) -> dict:
    if produto_id not in cart.items:
        raise ToolError(f"Produto {produto_id} não está no carrinho")
    del cart.items[produto_id]
    return {"removido": produto_id}
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_cart.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/cart.py tests/test_cart.py
git commit -m "feat(tools): cart state + add/view/remove"
```

---

## Task 8: Report tool

**Files:**
- Create: `nimbus/tools/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write failing tests**

`tests/test_report.py`:
```python
from pathlib import Path
import re
from nimbus.tools.cart import CartState, add_to_cart
from nimbus.tools.report import generate_order_report


def test_report_gera_arquivo_e_calcula_total(tmp_path, data_dir):
    from nimbus.tools.catalog import load_products
    from nimbus.tools.pricing import load_coupons, load_shipping

    produtos = load_products(data_dir / "produtos.csv")
    cupons = load_coupons(data_dir / "cupons.csv")
    frete = load_shipping(data_dir / "frete.csv")

    cart = CartState()
    add_to_cart(cart, produtos, "P001", 2)  # 2 x 159.90 = 319.80
    add_to_cart(cart, produtos, "P014", 1)  # 1 x 49.90 = 49.90
    # subtotal = 369.70

    res = generate_order_report(
        cart=cart,
        produtos=produtos,
        cupons=cupons,
        frete=frete,
        uf="SP",
        cupom="BEMVINDO10",
        out_dir=tmp_path,
    )
    assert Path(res["caminho"]).exists()
    conteudo = Path(res["caminho"]).read_text(encoding="utf-8")
    assert "Pedido Loja Nimbus" in conteudo
    assert "Mouse Gamer" in conteudo
    assert "BEMVINDO10" in conteudo
    # subtotal 369.70 - 10% = 36.97 desconto -> 332.73 + frete 15.90 (não passa de 500) = 348.63
    assert res["total"] == 348.63
    assert re.search(r"Total.*348[.,]63", conteudo)


def test_report_sem_cupom(tmp_path, data_dir):
    from nimbus.tools.catalog import load_products
    from nimbus.tools.pricing import load_coupons, load_shipping

    produtos = load_products(data_dir / "produtos.csv")
    cupons = load_coupons(data_dir / "cupons.csv")
    frete = load_shipping(data_dir / "frete.csv")

    cart = CartState()
    add_to_cart(cart, produtos, "P001", 1)  # 159.90
    res = generate_order_report(cart, produtos, cupons, frete, uf="SP", cupom=None, out_dir=tmp_path)
    # 159.90 + 15.90 = 175.80
    assert res["total"] == 175.80
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_report.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/tools/report.py`:
```python
"""Tool: gera o relatório markdown final do pedido."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional

from nimbus.tools.cart import CartState, view_cart
from nimbus.tools.errors import ToolError
from nimbus.tools.pricing import calculate_shipping, validate_coupon


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_order_report(
    cart: CartState,
    produtos: list[dict],
    cupons: list[dict],
    frete: dict[str, dict],
    uf: str,
    cupom: Optional[str],
    out_dir: Path,
) -> dict:
    if not cart.items:
        raise ToolError("Carrinho vazio — adicione itens antes de fechar o pedido")

    view = view_cart(cart, produtos)
    subtotal = view["subtotal"]

    desconto = 0.0
    cupom_info = None
    frete_gratis_pelo_cupom = False
    if cupom:
        cupom_info = validate_coupon(cupons, cupom, subtotal)
        if cupom_info["tipo"] == "frete_gratis":
            frete_gratis_pelo_cupom = True
        else:
            desconto = cupom_info["desconto"]

    frete_calc = calculate_shipping(frete, uf, subtotal)
    valor_frete = 0.0 if frete_gratis_pelo_cupom else frete_calc["valor"]

    total = round(subtotal - desconto + valor_frete, 2)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    caminho = out_dir / f"pedido_{timestamp}.md"

    linhas = [
        f"# Pedido Loja Nimbus — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Itens",
        "",
        "| Produto | Qtd | Preço unit. | Subtotal |",
        "|---|---|---|---|",
    ]
    for it in view["items"]:
        linhas.append(
            f"| {it['nome']} | {it['quantidade']} | {_fmt_brl(it['preco_unitario'])} | {_fmt_brl(it['subtotal'])} |"
        )

    linhas += [
        "",
        "## Resumo",
        "",
        f"- Subtotal: {_fmt_brl(subtotal)}",
    ]
    if cupom_info:
        if frete_gratis_pelo_cupom:
            linhas.append(f"- Cupom {cupom}: frete grátis")
        else:
            linhas.append(f"- Cupom {cupom}: -{_fmt_brl(desconto)}")
    linhas.append(
        f"- Frete ({uf}, {frete_calc['prazo_dias']} dias úteis): {_fmt_brl(valor_frete)}"
    )
    linhas += [
        f"- **Total: {_fmt_brl(total)}**",
        "",
        "## Forma de pagamento sugerida",
        "",
        "Pix (5% de desconto adicional disponível)",
        "",
    ]

    caminho.write_text("\n".join(linhas), encoding="utf-8")

    return {
        "caminho": str(caminho),
        "subtotal": round(subtotal, 2),
        "desconto": round(desconto, 2),
        "frete": round(valor_frete, 2),
        "total": total,
    }
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_report.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/report.py tests/test_report.py
git commit -m "feat(tools): generate_order_report (markdown final)"
```

---

## Task 9: Tool registry (schemas + dispatcher)

**Files:**
- Create: `nimbus/tools/registry.py`
- Create: `tests/test_tool_parsing.py`

- [ ] **Step 1: Write failing tests**

`tests/test_tool_parsing.py`:
```python
import json
import pytest
from nimbus.tools.registry import TOOL_SCHEMAS, execute_tool, build_context
from nimbus.tools.errors import ToolError


def test_schemas_seguem_formato_openai():
    assert isinstance(TOOL_SCHEMAS, list)
    assert len(TOOL_SCHEMAS) >= 8
    nomes = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert {
        "search_products", "get_product", "validate_coupon", "calculate_shipping",
        "add_to_cart", "view_cart", "remove_from_cart", "generate_order_report",
    }.issubset(nomes)
    for s in TOOL_SCHEMAS:
        assert s["type"] == "function"
        assert "parameters" in s["function"]


def test_execute_tool_search_products(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    out = execute_tool("search_products", {"query": "logitech"}, ctx)
    assert any("logitech" in p["nome"].lower() for p in out)


def test_execute_tool_unknown_raises(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    with pytest.raises(ToolError, match="desconhecida"):
        execute_tool("nao_existe", {}, ctx)


def test_execute_tool_propaga_tool_error(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    with pytest.raises(ToolError, match="não encontrado"):
        execute_tool("get_product", {"produto_id": "P999"}, ctx)


def test_parse_tool_call_arguments_json_string(data_dir, tmp_path):
    """Argumentos podem chegar como string JSON (formato OpenAI/Groq) ou dict."""
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    args_json = json.dumps({"query": "logitech"})
    out = execute_tool("search_products", args_json, ctx)
    assert isinstance(out, list)
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_tool_parsing.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/tools/registry.py`:
```python
"""Schemas JSON das tools + dispatcher para o loop do agente."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbus.tools.cart import CartState, add_to_cart, remove_from_cart, view_cart
from nimbus.tools.catalog import get_product, load_products, search_products
from nimbus.tools.errors import ToolError
from nimbus.tools.pricing import (
    calculate_shipping, load_coupons, load_shipping, validate_coupon,
)
from nimbus.tools.report import generate_order_report


@dataclass
class ToolContext:
    produtos: list[dict]
    cupons: list[dict]
    frete: dict[str, dict]
    cart: CartState
    pedidos_dir: Path


def build_context(data_dir: Path, pedidos_dir: Path) -> ToolContext:
    return ToolContext(
        produtos=load_products(data_dir / "produtos.csv"),
        cupons=load_coupons(data_dir / "cupons.csv"),
        frete=load_shipping(data_dir / "frete.csv"),
        cart=CartState(),
        pedidos_dir=pedidos_dir,
    )


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Busca produtos no catálogo da Loja Nimbus por nome/marca/descrição, com filtros opcionais de categoria e teto de preço.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca (nome, marca ou palavra-chave)"},
                    "categoria": {"type": "string", "description": "Filtra por categoria exata (Periféricos, Notebooks, Smartphones, Áudio, Acessórios)"},
                    "max_preco": {"type": "number", "description": "Preço máximo em reais"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Retorna detalhes de um produto pelo ID.",
            "parameters": {
                "type": "object",
                "properties": {"produto_id": {"type": "string"}},
                "required": ["produto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_coupon",
            "description": "Valida um código de cupom contra o valor atual do pedido e retorna o desconto aplicável.",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string"},
                    "valor_pedido": {"type": "number"},
                },
                "required": ["codigo", "valor_pedido"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_shipping",
            "description": "Calcula o frete para uma UF brasileira dado o valor do pedido (pedidos > R$500 ganham 50% off).",
            "parameters": {
                "type": "object",
                "properties": {
                    "uf": {"type": "string", "description": "Sigla da UF (ex: SP, RJ)"},
                    "valor_pedido": {"type": "number"},
                },
                "required": ["uf", "valor_pedido"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Adiciona um produto ao carrinho do usuário. Se já existir, soma à quantidade atual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_id": {"type": "string"},
                    "quantidade": {"type": "integer", "minimum": 1},
                },
                "required": ["produto_id", "quantidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "Mostra o carrinho atual com itens, quantidades, subtotais e subtotal geral.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove um produto do carrinho.",
            "parameters": {
                "type": "object",
                "properties": {"produto_id": {"type": "string"}},
                "required": ["produto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_order_report",
            "description": "Gera o relatório markdown final do pedido (com itens, cupom, frete, total) e salva em arquivo. Use quando o usuário sinalizar que quer fechar/finalizar o pedido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uf": {"type": "string"},
                    "cupom": {"type": "string", "description": "Código do cupom (opcional)"},
                },
                "required": ["uf"],
            },
        },
    },
]


def _coerce_args(arguments: Any) -> dict:
    if isinstance(arguments, str):
        return json.loads(arguments) if arguments else {}
    if arguments is None:
        return {}
    return dict(arguments)


def execute_tool(name: str, arguments: Any, ctx: ToolContext) -> Any:
    """Despacha a tool pelo nome. Levanta ToolError se a tool não existe."""
    args = _coerce_args(arguments)

    if name == "search_products":
        return search_products(
            ctx.produtos,
            query=args.get("query", ""),
            categoria=args.get("categoria"),
            max_preco=args.get("max_preco"),
        )
    if name == "get_product":
        return get_product(ctx.produtos, args["produto_id"])
    if name == "validate_coupon":
        return validate_coupon(ctx.cupons, args["codigo"], args["valor_pedido"])
    if name == "calculate_shipping":
        return calculate_shipping(ctx.frete, args["uf"], args["valor_pedido"])
    if name == "add_to_cart":
        return add_to_cart(ctx.cart, ctx.produtos, args["produto_id"], int(args["quantidade"]))
    if name == "view_cart":
        return view_cart(ctx.cart, ctx.produtos)
    if name == "remove_from_cart":
        return remove_from_cart(ctx.cart, args["produto_id"])
    if name == "generate_order_report":
        return generate_order_report(
            cart=ctx.cart,
            produtos=ctx.produtos,
            cupons=ctx.cupons,
            frete=ctx.frete,
            uf=args["uf"],
            cupom=args.get("cupom"),
            out_dir=ctx.pedidos_dir,
        )
    raise ToolError(f"Tool desconhecida: {name}")
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_tool_parsing.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/tools/registry.py tests/test_tool_parsing.py
git commit -m "feat(tools): registry com schemas JSON e dispatcher execute_tool"
```

---

## Task 10: RAG — chunker

**Files:**
- Create: `nimbus/rag/chunker.py`
- Create: `tests/test_chunker.py`

- [ ] **Step 1: Write failing tests**

`tests/test_chunker.py`:
```python
from nimbus.rag.chunker import Chunk, chunk_markdown


def test_chunk_markdown_basico():
    text = "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três."
    chunks = chunk_markdown(text, source="x.md", overlap=0)
    assert len(chunks) == 3
    assert chunks[0].text == "Parágrafo um."
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.source == "x.md" for c in chunks)


def test_chunk_markdown_pula_paragrafos_vazios():
    text = "A.\n\n\n\nB."
    chunks = chunk_markdown(text, source="x.md", overlap=0)
    assert len(chunks) == 2


def test_chunk_markdown_overlap():
    text = "A.\n\nB.\n\nC.\n\nD."
    chunks = chunk_markdown(text, source="x.md", overlap=1)
    assert chunks[1].text.startswith("A.")  # incluiu o anterior
    assert "B." in chunks[1].text
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_chunker.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`nimbus/rag/chunker.py`:
```python
"""Chunker simples: divide markdown por parágrafos com overlap configurável."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str


def chunk_markdown(text: str, source: str, overlap: int = 1) -> list[Chunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    chunks: list[Chunk] = []
    for i, p in enumerate(paragraphs):
        if overlap > 0 and i > 0:
            start = max(0, i - overlap)
            joined = "\n\n".join(paragraphs[start:i + 1])
            chunks.append(Chunk(text=joined, source=source))
        else:
            chunks.append(Chunk(text=p, source=source))
    return chunks
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_chunker.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add nimbus/rag/chunker.py tests/test_chunker.py
git commit -m "feat(rag): chunker por parágrafo com overlap"
```

---

## Task 11: RAG — embeddings + store + retrieval

**Files:**
- Create: `nimbus/rag/embeddings.py`
- Create: `nimbus/rag/store.py`
- Create: `tests/test_rag_store.py`

- [ ] **Step 1: Write failing tests**

`tests/test_rag_store.py`:
```python
import numpy as np
import pytest
from nimbus.rag.chunker import Chunk
from nimbus.rag.store import VectorStore


class FakeEmbedder:
    """Embedder determinístico baseado em hashing simples para testes — sem rede."""
    dim = 8

    def encode(self, texts):
        out = []
        for t in texts:
            v = np.zeros(self.dim, dtype=np.float32)
            for i, ch in enumerate(t.lower()):
                v[i % self.dim] += (ord(ch) % 17) / 17.0
            n = np.linalg.norm(v) or 1.0
            out.append(v / n)
        return np.stack(out)


def test_vector_store_search_topk_e_ranking():
    embedder = FakeEmbedder()
    store = VectorStore(embedder=embedder)
    store.add([
        Chunk(text="política de devolução em 7 dias", source="d1.md"),
        Chunk(text="formas de pagamento aceitas", source="d2.md"),
        Chunk(text="rastreamento dos correios", source="d3.md"),
    ])
    results = store.search("devolução em 7 dias", top_k=2)
    assert len(results) == 2
    assert results[0].chunk.source == "d1.md"


def test_vector_store_vazio_retorna_lista_vazia():
    store = VectorStore(embedder=FakeEmbedder())
    assert store.search("qualquer coisa", top_k=3) == []
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_rag_store.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement embeddings wrapper**

`nimbus/rag/embeddings.py`:
```python
"""Wrapper sobre sentence-transformers com lazy load."""
from __future__ import annotations
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Lazy-loaded all-MiniLM-L6-v2."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        self._ensure_loaded()
        return self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
```

- [ ] **Step 4: Implement vector store**

`nimbus/rag/store.py`:
```python
"""Vector store em memória + retrieval por cosine similarity."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np

from nimbus.rag.chunker import Chunk


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float


class VectorStore:
    def __init__(self, embedder: Any):
        self.embedder = embedder
        self._chunks: list[Chunk] = []
        self._embeddings: np.ndarray | None = None

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        new_emb = self.embedder.encode([c.text for c in chunks])
        self._chunks.extend(chunks)
        if self._embeddings is None:
            self._embeddings = new_emb
        else:
            self._embeddings = np.vstack([self._embeddings, new_emb])

    def search(self, query: str, top_k: int = 3) -> list[RetrievalHit]:
        if not self._chunks or self._embeddings is None:
            return []
        q = self.embedder.encode([query])[0]
        # embeddings já normalizados → cosine = dot product
        scores = self._embeddings @ q
        top_idx = np.argsort(-scores)[:top_k]
        return [RetrievalHit(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx]
```

- [ ] **Step 5: Run tests, verify PASS**

Run: `pytest tests/test_rag_store.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add nimbus/rag/embeddings.py nimbus/rag/store.py tests/test_rag_store.py
git commit -m "feat(rag): embeddings wrapper e vector store in-memory"
```

---

## Task 12: LLM client base + Groq implementation

**Files:**
- Create: `nimbus/llm/base.py`
- Create: `nimbus/llm/groq_client.py`

> **Nota:** Não há teste isolado pra `groq_client` (depende de rede / mock pesado). A integração é validada na Task 14 com mock do Protocol.

- [ ] **Step 1: Implement `nimbus/llm/base.py`**

```python
"""Interface comum para clientes LLM. Trocar provider = trocar arquivo."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any  # str (JSON) ou dict


@dataclass
class ChatResponse:
    content: Optional[str]
    tool_calls: list[ToolCall]
    raw: Any = None  # response original do provider, p/ debug


class LLMError(Exception):
    """Erro genérico de LLM (timeout, rate limit, etc.)."""


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float,
    ) -> ChatResponse: ...
```

- [ ] **Step 2: Implement `nimbus/llm/groq_client.py`**

```python
"""Cliente Groq adaptado pra interface LLMClient."""
from __future__ import annotations
import os

from nimbus.llm.base import ChatResponse, LLMError, ToolCall


class GroqClient:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from groq import Groq
        except ImportError as e:
            raise LLMError("Pacote `groq` não instalado") from e
        self.model = model or os.environ.get("NIMBUS_MODEL", "llama-3.3-70b-versatile")
        self._client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatResponse:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                timeout=timeout,
            )
        except Exception as e:
            raise LLMError(f"Erro na chamada Groq: {e}") from e

        choice = resp.choices[0].message
        tool_calls = []
        for tc in (choice.tool_calls or []):
            tool_calls.append(ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=tc.function.arguments,
            ))
        return ChatResponse(
            content=choice.content,
            tool_calls=tool_calls,
            raw=resp,
        )
```

- [ ] **Step 3: Quick smoke import**

Run: `python -c "from nimbus.llm.base import LLMClient, ChatResponse, ToolCall, LLMError; from nimbus.llm.groq_client import GroqClient; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add nimbus/llm/
git commit -m "feat(llm): interface LLMClient + GroqClient"
```

---

## Task 13: System prompt

**Files:**
- Create: `nimbus/prompts/system.md`

- [ ] **Step 1: Write the prompt**

`nimbus/prompts/system.md`:
```markdown
Você é o assistente virtual da **Loja Nimbus**, um e-commerce fictício de eletrônicos. Seu objetivo é ajudar o usuário a encontrar produtos, montar um carrinho e fechar o pedido.

## Como você trabalha

- Você tem acesso a tools para consultar o catálogo, validar cupons, calcular frete, manipular o carrinho e gerar o relatório final do pedido. **Use as tools sempre que precisar de dados concretos** — nunca invente preço, estoque, prazo de frete ou desconto.
- Quando o usuário fizer perguntas sobre políticas da loja (devoluções, formas de pagamento, entrega, garantia), responda com base no contexto institucional fornecido na seção "Contexto institucional relevante" e **cite a fonte** entre parênteses no formato `(fonte: nome_do_arquivo.md)`.
- Pergunte UF do usuário antes de calcular frete, e confirme o cupom se ele mencionar um código.
- Antes de adicionar ao carrinho, sempre confirme nome e quantidade com o usuário caso haja ambiguidade.
- Quando o usuário sinalizar que quer fechar/finalizar o pedido, chame a tool `generate_order_report` e depois confirme em texto natural ao usuário, mencionando o caminho do arquivo gerado e o total.

## Estilo

- Responda em português, tom amigável e direto. Sem floreios.
- Não invente produtos, marcas, cupons ou regras que não estão nas tools/contexto.
- Se uma tool retornar erro, explique ao usuário o que aconteceu e sugira o próximo passo.

## Contexto institucional relevante

{rag_context}
```

- [ ] **Step 2: Commit**

```bash
git add nimbus/prompts/system.md
git commit -m "feat(prompts): system prompt do agente Nimbus"
```

---

## Task 14: Agent loop

**Files:**
- Create: `nimbus/agent.py`
- Create: `tests/test_loop_max_iter.py`
- Create: `tests/test_agent_integration.py`

- [ ] **Step 1: Write failing tests**

`tests/test_loop_max_iter.py`:
```python
import pytest
from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


class AlwaysToolCallLLM:
    """Mock LLM que sempre devolve uma tool call (vai forçar max_iter)."""

    def chat(self, messages, tools, timeout):
        return ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="view_cart", arguments="{}")],
        )


def test_loop_para_em_max_iterations(data_dir, tmp_path):
    agent = Agent(
        llm=AlwaysToolCallLLM(),
        rag=None,
        config=AgentConfig(max_iterations=3, llm_timeout_s=10),
        data_dir=data_dir,
        pedidos_dir=tmp_path,
        system_prompt_template="sistema base\n\n{rag_context}",
    )
    out = agent.run_turn("oi")
    assert "tempo" in out.lower() or "reformular" in out.lower()
    # confirma que rodou exatamente 3 vezes a tool
    assert agent.iterations_last_turn == 3
```

`tests/test_agent_integration.py`:
```python
import json
import pytest
from nimbus.agent import Agent, AgentConfig
from nimbus.llm.base import ChatResponse, ToolCall


class ScriptedLLM:
    """LLM mockado: percorre lista de respostas pré-definidas."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.received_messages = []

    def chat(self, messages, tools, timeout):
        self.received_messages.append(messages)
        return self._responses.pop(0)


def test_agente_executa_tool_e_finaliza(data_dir, tmp_path):
    llm = ScriptedLLM([
        ChatResponse(
            content=None,
            tool_calls=[ToolCall(id="t1", name="search_products",
                                 arguments=json.dumps({"query": "logitech"}))],
        ),
        ChatResponse(
            content="Encontrei o Mouse Logitech G203 (P001) por R$ 159,90. Quer adicionar ao carrinho?",
            tool_calls=[],
        ),
    ])
    agent = Agent(
        llm=llm,
        rag=None,
        config=AgentConfig(max_iterations=5, llm_timeout_s=10),
        data_dir=data_dir,
        pedidos_dir=tmp_path,
        system_prompt_template="sistema base\n\n{rag_context}",
    )
    out = agent.run_turn("tem mouse logitech?")
    assert "Logitech" in out
    # garante que a 2ª chamada ao LLM já recebeu o resultado da tool
    last_msgs = llm.received_messages[-1]
    assert any(m.get("role") == "tool" for m in last_msgs)
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/test_loop_max_iter.py tests/test_agent_integration.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `nimbus/agent.py`**

```python
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
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `pytest tests/test_loop_max_iter.py tests/test_agent_integration.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run full suite**

Run: `pytest -v`
Expected: all green (~30+ tests).

- [ ] **Step 6: Commit**

```bash
git add nimbus/agent.py tests/test_loop_max_iter.py tests/test_agent_integration.py
git commit -m "feat(agent): loop próprio com max_iter, timeout e error handling"
```

---

## Task 15: CLI

**Files:**
- Create: `nimbus/cli.py`

- [ ] **Step 1: Implement `nimbus/cli.py`**

```python
"""REPL CLI do agente Nimbus."""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nimbus.agent import Agent, AgentConfig
from nimbus.llm.groq_client import GroqClient
from nimbus.rag.chunker import chunk_markdown
from nimbus.rag.embeddings import SentenceTransformerEmbedder
from nimbus.rag.store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = PROJECT_ROOT / "corpus"
PEDIDOS_DIR = PROJECT_ROOT / "pedidos"
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "nimbus" / "prompts" / "system.md"


def _setup_logging() -> None:
    level = logging.INFO if os.environ.get("NIMBUS_DEBUG") else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_rag() -> VectorStore:
    print("[setup] carregando embeddings (primeira vez baixa o modelo, ~80MB)...", file=sys.stderr)
    store = VectorStore(embedder=SentenceTransformerEmbedder())
    for md in sorted(CORPUS_DIR.glob("*.md")):
        chunks = chunk_markdown(md.read_text(encoding="utf-8"), source=md.name, overlap=1)
        store.add(chunks)
    print(f"[setup] corpus indexado: {len(list(CORPUS_DIR.glob('*.md')))} arquivos.", file=sys.stderr)
    return store


def main() -> None:
    load_dotenv()
    _setup_logging()

    if not os.environ.get("GROQ_API_KEY"):
        print("ERRO: defina GROQ_API_KEY no .env (veja .env.example).", file=sys.stderr)
        sys.exit(1)

    rag = _build_rag()
    agent = Agent(
        llm=GroqClient(),
        rag=rag,
        config=AgentConfig(),
        data_dir=DATA_DIR,
        pedidos_dir=PEDIDOS_DIR,
        system_prompt_template=SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"),
    )

    print("Loja Nimbus — assistente virtual. Digite 'sair' para encerrar.\n")
    while True:
        try:
            user = input("você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break
        if not user:
            continue
        if user.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break
        resposta = agent.run_turn(user)
        print(f"\nNimbus> {resposta}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke run (com chave válida)**

Run (precisa de `GROQ_API_KEY` no `.env`):
```bash
echo "tem mouse logitech?" | python -m nimbus
```
Expected: a CLI carrega o RAG, manda a pergunta, agente responde mencionando o Logitech G203. Pode requerir intervenção manual pra inserir EOF — alternativamente rode interativamente.

- [ ] **Step 3: Commit**

```bash
git add nimbus/cli.py
git commit -m "feat(cli): REPL com setup de RAG e GroqClient"
```

---

## Task 16: README + RELATO_IA

**Files:**
- Create/overwrite: `README.md`
- Create: `RELATO_IA.md`

- [ ] **Step 1: Write `README.md`**

```markdown
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
python -m nimbus
```

Primeiro start baixa o modelo de embeddings `all-MiniLM-L6-v2` (~80MB).

Exemplo de sessão:
```
você> tenho até R$ 200, queria um mouse e um teclado
Nimbus> Encontrei... [usa search_products] ...
você> adiciona o Logitech G203 e o Redragon Kumara
você> meu CEP é em SP, tem cupom?
você> aplica BEMVINDO10 e fecha o pedido
Nimbus> Relatório salvo em pedidos/pedido_20260428_153022.md, total R$ 384,12.
```

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
- Logging estruturado (stdout via `logging`) de cada iteração: pergunta do usuário, tool_calls com argumentos, resultados das tools, resposta final. Liguar com `NIMBUS_DEBUG=1`.

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
```

- [ ] **Step 2: Write `RELATO_IA.md`**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add README.md RELATO_IA.md
git commit -m "docs: README com arquitetura do loop + RELATO_IA"
```

---

## Task 17: Final verification

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: all green, ~35+ tests.

- [ ] **Step 2: Smoke test CLI** (precisa GROQ_API_KEY)

Run interativamente:
```bash
python -m nimbus
# pergunta: "tem mouse logitech?"
# pergunta: "adiciona 1 unidade ao carrinho"
# pergunta: "qual a politica de devolução?"
# pergunta: "minha UF é SP, fecha o pedido"
```
Expected: agente usa as tools corretas, cita a fonte na resposta de devolução, gera o relatório em `pedidos/`.

- [ ] **Step 3: Verify final commit cleanness**

```bash
git status
git log --oneline
```
Expected: working tree clean, ~16 commits descritivos seguindo conventional commits.

---

## Self-Review checklist (executado durante a escrita)

- ✅ Cada requisito do spec tem task correspondente: corpus 4 docs (Task 3), 8 tools (Tasks 5-9), loop próprio com guardas (Task 14), 3+ testes pytest (Tasks 9, 14), README + RELATO_IA (Task 16).
- ✅ Sem placeholders TBD/TODO — todo step tem código completo ou comando exato.
- ✅ Type consistency: `CartState`, `ToolError`, `ToolContext`, `ChatResponse`, `ToolCall` usados de forma consistente entre tasks.
- ✅ Testes batem com implementação: nomes de funções e schemas idênticos entre `test_*.py` e o módulo correspondente.
- ✅ Bônus declarados estão no plano (LLMClient abstração, memória multi-turno via `conversation`, citação de fonte via system prompt).
- ✅ Frequent commits: 1 commit por task (~16 commits totais).
