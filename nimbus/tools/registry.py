"""Schemas JSON das tools + dispatcher para o loop do agente."""
from __future__ import annotations
import json
from dataclasses import dataclass
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
                    "categoria": {"type": "string", "description": "Filtra por categoria exata (Perifericos, Notebooks, Smartphones, Audio, Acessorios) — sem acentos"},
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
