import pytest
from nimbus.tools.catalog import load_products, search_products, get_product
from nimbus.tools.errors import ToolError


def test_load_products_returns_all_rows(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    assert len(produtos) >= 20
    assert produtos[0]["id"] == "P001"
    assert isinstance(produtos[0]["preco"], float)
    assert isinstance(produtos[0]["estoque"], int)


def test_search_products_by_query(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="logitech")
    assert len(results) >= 1
    assert all("logitech" in p["nome"].lower() or "logitech" in p["marca"].lower() for p in results)


def test_search_products_by_categoria(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="", categoria="Notebooks")
    assert len(results) >= 1
    assert all(p["categoria"] == "Notebooks" for p in results)


def test_search_products_by_max_preco(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="", max_preco=100.0)
    assert all(p["preco"] <= 100.0 for p in results)


def test_get_product_found(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    p = get_product(produtos, "P001")
    assert p["nome"].startswith("Mouse Gamer")


def test_get_product_not_found_raises(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    with pytest.raises(ToolError, match="não encontrado"):
        get_product(produtos, "P999")
