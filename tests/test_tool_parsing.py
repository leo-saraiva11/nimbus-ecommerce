import json
import pytest
from nimbus.tools.registry import TOOL_SCHEMAS, execute_tool, build_context
from nimbus.tools.errors import ToolError


def test_schemas_seguem_formato_openai():
    assert isinstance(TOOL_SCHEMAS, list)
    assert len(TOOL_SCHEMAS) >= 9
    nomes = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert {
        "search_products", "get_product", "validate_coupon", "calculate_shipping",
        "add_to_cart", "view_cart", "remove_from_cart", "generate_order_report",
        "search_policies",
    }.issubset(nomes)
    for s in TOOL_SCHEMAS:
        assert s["type"] == "function"
        assert "parameters" in s["function"]


def test_search_policies_usa_rag_quando_disponivel(data_dir, tmp_path):
    """A tool search_policies devolve trechos do vector store passado em build_context."""
    from dataclasses import dataclass

    @dataclass
    class _C:
        text: str
        source: str

    @dataclass
    class _H:
        chunk: object
        score: float

    class _StubRAG:
        def search(self, query, top_k=3):
            return [_H(_C("trecho institucional", "politica.md"), 0.91)]

    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path, rag=_StubRAG())
    out = execute_tool("search_policies", {"query": "como devolver?"}, ctx)
    assert out == [{"fonte": "politica.md", "score": 0.91, "trecho": "trecho institucional"}]


def test_search_policies_sem_rag_levanta_tool_error(data_dir, tmp_path):
    ctx = build_context(data_dir=data_dir, pedidos_dir=tmp_path, rag=None)
    with pytest.raises(ToolError, match="não disponível"):
        execute_tool("search_policies", {"query": "qualquer coisa"}, ctx)


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
