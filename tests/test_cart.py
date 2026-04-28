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
