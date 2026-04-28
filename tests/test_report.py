from pathlib import Path
import re
from nimbus.tools.cart import CartState, add_to_cart
from nimbus.tools.report import generate_order_report


def _load_all(data_dir):
    from nimbus.tools.catalog import load_products
    from nimbus.tools.pricing import load_coupons, load_shipping
    return (
        load_products(data_dir / "produtos.csv"),
        load_coupons(data_dir / "cupons.csv"),
        load_shipping(data_dir / "frete.csv"),
    )


def test_report_gera_arquivo_e_calcula_total(tmp_path, data_dir):
    produtos, cupons, frete = _load_all(data_dir)
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 2)  # 2 x 159.90 = 319.80
    add_to_cart(cart, produtos, "P014", 1)  # 1 x 49.90 = 49.90
    # subtotal = 369.70

    res = generate_order_report(
        cart=cart, produtos=produtos, cupons=cupons, frete=frete,
        uf="SP", cupom="BEMVINDO10", out_dir=tmp_path,
    )
    assert Path(res["caminho"]).exists()
    conteudo = Path(res["caminho"]).read_text(encoding="utf-8")
    assert "Pedido Loja Nimbus" in conteudo
    assert "Mouse Gamer" in conteudo
    assert "BEMVINDO10" in conteudo
    # subtotal 369.70 - 10% = 36.97 desconto -> 332.73 + frete 15.90 = 348.63
    assert res["total"] == 348.63
    assert re.search(r"Total.*348[.,]63", conteudo)


def test_report_sem_cupom(tmp_path, data_dir):
    produtos, cupons, frete = _load_all(data_dir)
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 1)  # 159.90
    res = generate_order_report(cart, produtos, cupons, frete, uf="SP", cupom=None, out_dir=tmp_path)
    assert res["total"] == 175.80


def test_report_pix_aplica_5pct_de_desconto(tmp_path, data_dir):
    """forma_pagamento='pix' deve descontar 5% sobre subtotal-cupom."""
    produtos, cupons, frete = _load_all(data_dir)
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 1)  # 159.90
    res = generate_order_report(
        cart, produtos, cupons, frete,
        uf="SP", cupom=None, out_dir=tmp_path, forma_pagamento="pix",
    )
    # 159.90 - 5% = 8.00 desconto pix → 151.90 + 15.90 frete = 167.80
    assert res["desconto_pix"] == 7.99 or res["desconto_pix"] == 8.00  # arredondamento
    assert abs(res["total"] - 167.80) < 0.05
    assert res["forma_pagamento"] == "pix"
    conteudo = Path(res["caminho"]).read_text(encoding="utf-8")
    assert "Desconto Pix" in conteudo


def test_report_pix_combinado_com_cupom(tmp_path, data_dir):
    """Cupom percentual + Pix: ambos aplicados, na ordem cupom→pix sobre o resto."""
    produtos, cupons, frete = _load_all(data_dir)
    cart = CartState()
    add_to_cart(cart, produtos, "P002", 1)  # 249.90
    res = generate_order_report(
        cart, produtos, cupons, frete,
        uf="SP", cupom="BEMVINDO10", out_dir=tmp_path, forma_pagamento="pix",
    )
    # subtotal=249.90, cupom 10%=24.99, base_pos_cupom=224.91, pix 5%=11.25
    # total = 249.90 - 24.99 - 11.25 + 15.90 = 229.56
    assert res["desconto_cupom"] == 24.99
    assert res["desconto_pix"] == 11.25
    assert abs(res["total"] - 229.56) < 0.05


def test_report_forma_pagamento_invalida_nao_aplica_pix(tmp_path, data_dir):
    produtos, cupons, frete = _load_all(data_dir)
    cart = CartState()
    add_to_cart(cart, produtos, "P001", 1)
    res = generate_order_report(
        cart, produtos, cupons, frete,
        uf="SP", cupom=None, out_dir=tmp_path, forma_pagamento="cartao",
    )
    assert res["desconto_pix"] == 0.0
