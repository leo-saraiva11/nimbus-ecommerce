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
