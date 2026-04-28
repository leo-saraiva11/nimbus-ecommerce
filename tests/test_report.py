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
