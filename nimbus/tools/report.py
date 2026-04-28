"""Tool: gera o relatório markdown final do pedido."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional

from nimbus.tools.cart import CartState, view_cart
from nimbus.tools.errors import ToolError
from nimbus.tools.pricing import calculate_shipping, validate_coupon

PIX_DISCOUNT_RATE = 0.05  # 5% adicional pra pagamento via Pix (regra automática da loja)


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
    forma_pagamento: Optional[str] = None,
) -> dict:
    """Gera o relatório do pedido. Suporta cupom (validado em ``cupons.csv``) e
    a regra automática de **5% off para pagamento via Pix** — passe
    ``forma_pagamento="pix"`` (case insensitive). Pix NÃO é cupom; é regra
    institucional descrita em ``corpus/formas_pagamento.md``.
    """
    if not cart.items:
        raise ToolError("Carrinho vazio — adicione itens antes de fechar o pedido")

    view = view_cart(cart, produtos)
    subtotal = view["subtotal"]

    desconto_cupom = 0.0
    cupom_info = None
    frete_gratis_pelo_cupom = False
    if cupom:
        cupom_info = validate_coupon(cupons, cupom, subtotal)
        if cupom_info["tipo"] == "frete_gratis":
            frete_gratis_pelo_cupom = True
        else:
            desconto_cupom = cupom_info["desconto"]

    base_pos_cupom = max(0.0, subtotal - desconto_cupom)
    pix = bool(forma_pagamento) and forma_pagamento.lower() == "pix"
    desconto_pix = round(base_pos_cupom * PIX_DISCOUNT_RATE, 2) if pix else 0.0

    frete_calc = calculate_shipping(frete, uf, subtotal)
    valor_frete = 0.0 if frete_gratis_pelo_cupom else frete_calc["valor"]

    total = round(subtotal - desconto_cupom - desconto_pix + valor_frete, 2)

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
            linhas.append(f"- Cupom {cupom}: -{_fmt_brl(desconto_cupom)}")
    if pix:
        linhas.append(f"- Desconto Pix (5%): -{_fmt_brl(desconto_pix)}")
    linhas.append(
        f"- Frete ({uf}, {frete_calc['prazo_dias']} dias úteis): {_fmt_brl(valor_frete)}"
    )
    linhas += [
        f"- **Total: {_fmt_brl(total)}**",
        "",
        "## Forma de pagamento",
        "",
        f"{'Pix (5% de desconto aplicado)' if pix else 'A definir no checkout (Pix dá 5% off automático)'}",
        "",
    ]

    caminho.write_text("\n".join(linhas), encoding="utf-8")

    return {
        "caminho": str(caminho),
        "subtotal": round(subtotal, 2),
        "desconto_cupom": round(desconto_cupom, 2),
        "desconto_pix": desconto_pix,
        "frete": round(valor_frete, 2),
        "total": total,
        "forma_pagamento": "pix" if pix else (forma_pagamento or "indefinida"),
    }
