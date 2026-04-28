import json
import pytest
from nimbus.tools.registry import TOOL_SCHEMAS, execute_tool, build_context
from nimbus.tools.errors import ToolError


def test_schemas_seguem_formato_openai():
    assert isinstance(TOOL_SCHEMAS, list)
    assert len(TOOL_SCHEMAS) >= 8
    nomes = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert {
        "search_products", "get_product", "validate_coupon", "calculate_shipping",
        "add_to_cart", "view_cart", "remove_from_cart", "generate_order_report",
    }.issubset(nomes)
    for s in TOOL_SCHEMAS:
        assert s["type"] == "function"
        assert "parameters" in s["function"]


def test_execute_tool_search_products(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    out = execute_tool("search_products", {"query": "logitech"}, ctx)
    assert any("logitech" in p["nome"].lower() for p in out)


def test_execute_tool_unknown_raises(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    with pytest.raises(ToolError, match="desconhecida"):
        execute_tool("nao_existe", {}, ctx)


def test_execute_tool_propaga_tool_error(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    with pytest.raises(ToolError, match="não encontrado"):
        execute_tool("get_product", {"produto_id": "P999"}, ctx)


def test_parse_tool_call_arguments_json_string(data_dir, tmp_path):
    """Argumentos podem chegar como string JSON (formato OpenAI/Groq) ou dict."""
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path)
    args_json = json.dumps({"query": "logitech"})
    out = execute_tool("search_products", args_json, ctx)
    assert isinstance(out, list)
