from src.logic.tools import ToolRegistry


def test_tool_registry_calculator():
    res = ToolRegistry.execute_tool("calculator", {"expression": "1+2*3"})
    assert res == "7"


def test_tool_registry_get_current_time():
    res = ToolRegistry.execute_tool("get_current_time", {})
    assert isinstance(res, str)
    assert len(res) >= 10
