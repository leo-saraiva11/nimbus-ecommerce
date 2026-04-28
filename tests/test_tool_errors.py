from nimbus.tools.errors import ToolError


def test_tool_error_carries_message():
    err = ToolError("produto não encontrado")
    assert str(err) == "produto não encontrado"
    assert isinstance(err, Exception)
