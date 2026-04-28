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
