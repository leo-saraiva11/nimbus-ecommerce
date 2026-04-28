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


def test_search_products_max_preco_zero_eh_sem_filtro(data_dir):
    """LLM frequentemente passa max_preco=0 querendo dizer 'ignora teto'.
    Tratamos como 'sem filtro' em vez de filtrar produtos com preço <= 0."""
    produtos = load_products(data_dir / "produtos.csv")
    results = search_products(produtos, query="", categoria="Notebooks", max_preco=0)
    assert len(results) >= 1
    # confirma que não retornou só produtos baratos — todos os notebooks aparecem
    precos = [p["preco"] for p in results]
    assert max(precos) > 1000  # se filtrasse por <=0 estaria vazio


def test_get_product_found(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    p = get_product(produtos, "P001")
    assert p["nome"].startswith("Mouse Gamer")


def test_get_product_not_found_raises(data_dir):
    produtos = load_products(data_dir / "produtos.csv")
    with pytest.raises(ToolError, match="não encontrado"):
        get_product(produtos, "P999")
