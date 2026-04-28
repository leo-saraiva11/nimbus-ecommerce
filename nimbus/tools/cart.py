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
            f"estoque insuficiente para {produto['nome']}: disponível {produto['estoque']}, solicitado {nova}"
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
