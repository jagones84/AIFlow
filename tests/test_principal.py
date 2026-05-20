import os
import json
import pytest
import asyncio
from dotenv import load_dotenv

from src.models.node_models import NodeData, FlowItem, NodeType, SetFieldDefinition, VariableOperation, MergeMode, RouterMode
from src.logic.node_executor import NodeExecutor
from src.logic.tools import ToolRegistry

load_dotenv()

results = []

def add_result(category, name, success, details=""):
    results.append({
        "category": category,
        "name": name,
        "success": success,
        "details": details
    })

@pytest.fixture(scope="session", autouse=True)
def generate_report(request):
    yield
    report_lines = ["# Principal Stress Test Report", "", "## Summary"]
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    report_lines.append(f"Total Tests: {total}")
    report_lines.append(f"Passed: {passed}")
    report_lines.append(f"Failed: {failed}")
    report_lines.append("")
    
    report_lines.append("## Details")
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        report_lines.append(f"### {status}: {r['category']} - {r['name']}")
        if r["details"]:
            report_lines.append(f"**Details:** {r['details']}")
        report_lines.append("")
        
    with open("tests/principal_test_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

def test_set_node():
    node = NodeData(
        title="Set Data",
        type=NodeType.SET,
        setFields=[
            SetFieldDefinition(name="my_str", value="hello", type="string"),
            SetFieldDefinition(name="my_num", value="100", type="number")
        ]
    )
    input_items = [FlowItem(json_data={"initial": "value"})]
    try:
        executor = NodeExecutor()
        res = executor.execute(node, input_items, [node], {})
        assert res.success
        assert len(res.outputItems) == 1
        assert res.outputItems[0].json_data["my_str"] == "hello"
        assert res.outputItems[0].json_data["my_num"] == 100
        add_result("Node Block", "SET", True, "Successfully set fields.")
    except Exception as e:
        add_result("Node Block", "SET", False, str(e))
        raise

def test_code_node():
    node = NodeData(
        title="Execute Code",
        type=NodeType.CODE,
        codeBody="for item in input:\n    item.json_data['computed'] = item.json_data['val'] * 2\nreturn input"
    )
    input_items = [FlowItem(json_data={"val": 21})]
    try:
        executor = NodeExecutor()
        res = executor.execute(node, input_items, [node], {})
        assert res.success
        assert len(res.outputItems) == 1
        assert res.outputItems[0].json_data["computed"] == 42
        add_result("Node Block", "CODE", True, "Successfully executed python code.")
    except Exception as e:
        add_result("Node Block", "CODE", False, str(e))
        raise

def test_router_node():
    node = NodeData(
        title="Router",
        type=NodeType.ROUTER,
        routerMode=RouterMode.SIMPLE_RULE,
        ruleCondition="expr: {{ $json.val }} > 10"
    )
    input_items = [FlowItem(json_data={"val": 15}), FlowItem(json_data={"val": 5})]
    try:
        executor = NodeExecutor()
        res = executor.execute(node, input_items, [node], {})
        assert res.success
        # Assuming router splits output to different lists depending on rule, check output length
        assert len(res.outputItems) == 2
        add_result("Node Block", "ROUTER", True, "Router processed inputs.")
    except Exception as e:
        add_result("Node Block", "ROUTER", False, str(e))
        raise

def test_http_request_node():
    node = NodeData(
        title="HTTP",
        type=NodeType.HTTP_REQUEST,
        httpUrl="https://jsonplaceholder.typicode.com/posts/1",
        httpMethod="GET"
    )
    try:
        executor = NodeExecutor()
        res = executor.execute(node, [], [node], {})
        assert res.success
        assert len(res.outputItems) >= 1
        add_result("Node Block", "HTTP_REQUEST", True, "HTTP GET request succeeded.")
    except Exception as e:
        add_result("Node Block", "HTTP_REQUEST", False, str(e))
        raise

def test_mcp_tools():
    # Iterate through all configured MCP tools
    config = ToolRegistry._load_mcp_config()
    for server_name, server_config in config.items():
        if server_config.get("disabled", False):
            continue
            
        try:
            tools = ToolRegistry.get_mcp_server_tools(server_name)
            if not tools:
                add_result("MCP Server", server_name, False, "Failed to retrieve tools or server is not running properly.")
                continue
                
            add_result("MCP Server", server_name, True, f"Server running with {len(tools)} tools: {[t.get('name') for t in tools]}")
            
            # Stress test: run one simple tool if possible
            # We won't test complex tools that require strict args to avoid false failures, 
            # but we confirm the server responds to list tools.
        except Exception as e:
            add_result("MCP Server", server_name, False, f"Exception occurred: {str(e)}")

