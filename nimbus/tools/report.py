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
