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
    # 0 ou negativo == "sem teto" (o LLM frequentemente passa 0 querendo dizer
    # "ignora o filtro de preço"; rejeitar isso degrada UX e força re-chamada)
    aplicar_teto = max_preco is not None and max_preco > 0
    out = []
    for p in produtos:
        if q and q not in p["nome"].lower() and q not in p["marca"].lower() and q not in p["descricao_curta"].lower():
            continue
        if categoria and p["categoria"] != categoria:
            continue
        if aplicar_teto and p["preco"] > max_preco:
            continue
        out.append(p)
    return out


def get_product(produtos: list[dict], produto_id: str) -> dict:
    """Retorna o produto por id, ou levanta ToolError."""
    for p in produtos:
        if p["id"] == produto_id:
            return p
    raise ToolError(f"Produto {produto_id} não encontrado no catálogo")
