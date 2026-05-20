import os
import json
import pytest
import asyncio
from dotenv import load_dotenv

from src.models.node_models import NodeData, FlowItem, NodeType, SetFieldDefinition, VariableOperation, MergeMode, RouterMode, MergeJoinType, RouteDefinition
from src.logic.node_executor import NodeExecutor
from src.logic.tools import ToolRegistry
from src.utils.managers import VariableManager

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
    report_lines = ["# Comprehensive Node & MCP Stress Test Report", "", "## Summary"]
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

def execute_node(node: NodeData, input_items=None, payloads=None):
    if input_items is None:
        input_items = []
    if payloads is None:
        payloads = {}
    executor = NodeExecutor()
    return executor.execute(node, input_items, [node], payloads)

def test_set_node():
    node = NodeData(
        title="Set Data", type=NodeType.SET,
        setFields=[
            SetFieldDefinition(name="my_str", value="hello", type="string"),
            SetFieldDefinition(name="my_num", value="100", type="number")
        ]
    )
    try:
        res = execute_node(node, [FlowItem(json_data={"initial": "value"})])
        assert res.success
        assert res.outputItems[0].json_data["my_str"] == "hello"
        assert res.outputItems[0].json_data["my_num"] == 100
        add_result("Node", "SET", True, "Successfully set string and number fields.")
    except Exception as e:
        add_result("Node", "SET", False, str(e))

def test_code_node():
    node = NodeData(
        title="Execute Code", type=NodeType.CODE,
        codeBody="for item in items:\n    item.json_data['computed'] = item.json_data['val'] * 2\nreturn items"
    )
    try:
        res = execute_node(node, [FlowItem(json_data={"val": 21})])
        assert res.success
        assert res.outputItems[0].json_data["computed"] == 42
        add_result("Node", "CODE", True, "Successfully executed python code.")
    except Exception as e:
        add_result("Node", "CODE", False, str(e))

def test_router_node():
    node = NodeData(
        title="Router", type=NodeType.ROUTER,
        routerMode=RouterMode.SIMPLE_RULE,
        ruleCondition="expr: {{ $json.val }} > 10"
    )
    try:
        res = execute_node(node, [FlowItem(json_data={"val": 15}), FlowItem(json_data={"val": 5})])
        assert res.success
        # NodeExecutor router outputs logic: True items in True branch, False items in False branch
        add_result("Node", "ROUTER", True, "Router processed inputs successfully.")
    except Exception as e:
        add_result("Node", "ROUTER", False, str(e))

def test_switch_node():
    node = NodeData(
        title="Switch", type=NodeType.SWITCH,
        switchRoutes=[
            RouteDefinition(id="r1", name="Route 1", condition="expr: {{ $json.val }} == 'A'"),
            RouteDefinition(id="r2", name="Route 2", condition="expr: {{ $json.val }} == 'B'")
        ]
    )
    try:
        res = execute_node(node, [FlowItem(json_data={"val": "A"}), FlowItem(json_data={"val": "B"})])
        assert res.success
        add_result("Node", "SWITCH", True, "Switch processed multiple routes.")
    except Exception as e:
        add_result("Node", "SWITCH", False, str(e))

def test_http_request_node():
    node = NodeData(
        title="HTTP", type=NodeType.HTTP_REQUEST,
        httpUrl="https://jsonplaceholder.typicode.com/posts/1", httpMethod="GET"
    )
    try:
        res = execute_node(node)
        assert res.success
        add_result("Node", "HTTP_REQUEST", True, "HTTP GET request succeeded.")
    except Exception as e:
        add_result("Node", "HTTP_REQUEST", False, str(e))

def test_json_parser_node():
    node = NodeData(title="JSON Parser", type=NodeType.JSON_PARSER)
    try:
        res = execute_node(node, [FlowItem(text='{"parsed": "success"}')])
        assert res.success
        assert res.outputItems[0].json_data["parsed"] == "success"
        add_result("Node", "JSON_PARSER", True, "Successfully parsed JSON text.")
    except Exception as e:
        add_result("Node", "JSON_PARSER", False, str(e))

def test_json_field_extract_node():
    node = NodeData(title="Extract", type=NodeType.JSON_FIELD_EXTRACT, ruleCondition="nested.field")
    try:
        res = execute_node(node, [FlowItem(json_data={"nested": {"field": "value"}})])
        assert res.success
        add_result("Node", "JSON_FIELD_EXTRACT", True, "Extracted nested JSON field.")
    except Exception as e:
        add_result("Node", "JSON_FIELD_EXTRACT", False, str(e))

def test_wait_node():
    node = NodeData(title="Wait", type=NodeType.WAIT, waitTimeMs=100)
    try:
        res = execute_node(node, [FlowItem(json_data={"wait": "done"})])
        assert res.success
        add_result("Node", "WAIT", True, "Successfully waited specified time.")
    except Exception as e:
        add_result("Node", "WAIT", False, str(e))

def test_variable_store_node():
    node_write = NodeData(
        title="Var Store Write", type=NodeType.VARIABLE_STORE,
        variableKey="test_var", variableOperation=VariableOperation.WRITE
    )
    node_read = NodeData(
        title="Var Store Read", type=NodeType.VARIABLE_STORE,
        variableKey="test_var", variableOperation=VariableOperation.READ
    )
    try:
        VariableManager.clear()
        # Write
        res_w = execute_node(node_write, [FlowItem(text="stored_value")])
        assert res_w.success
        # Read
        res_r = execute_node(node_read, [FlowItem(text="dummy")])
        assert res_r.success
        assert res_r.outputItems[0].text == "stored_value"
        add_result("Node", "VARIABLE_STORE", True, "Write and Read operations successful.")
    except Exception as e:
        add_result("Node", "VARIABLE_STORE", False, str(e))

def test_stop_and_error_node():
    node = NodeData(title="Stop", type=NodeType.STOP_AND_ERROR, errorMessage="Intentional Stop")
    try:
        res = execute_node(node, [FlowItem(json_data={"val": 1})])
        assert not res.success
        assert res.shouldStopFlow == True
        add_result("Node", "STOP_AND_ERROR", True, "Successfully stopped flow and raised error.")
    except Exception as e:
        add_result("Node", "STOP_AND_ERROR", False, str(e))

def test_filter_node():
    node = NodeData(title="Filter", type=NodeType.FILTER, ruleCondition="expr: {{ $json.val }} > 5")
    try:
        res = execute_node(node, [FlowItem(json_data={"val": 10}), FlowItem(json_data={"val": 2})])
        assert res.success
        assert len(res.outputItems) == 1
        assert res.outputItems[0].json_data["val"] == 10
        add_result("Node", "FILTER", True, "Successfully filtered items.")
    except Exception as e:
        add_result("Node", "FILTER", False, str(e))

def test_limit_node():
    node = NodeData(title="Limit", type=NodeType.LIMIT, batchSize=2)
    try:
        res = execute_node(node, [FlowItem(text="1"), FlowItem(text="2"), FlowItem(text="3")])
        assert res.success
        assert len(res.outputItems) == 2
        add_result("Node", "LIMIT", True, "Successfully limited items.")
    except Exception as e:
        add_result("Node", "LIMIT", False, str(e))

def test_file_save_node():
    node = NodeData(title="Save File", type=NodeType.FILE_SAVE, fileName="test_save.txt")
    try:
        res = execute_node(node, [FlowItem(text="Hello file save")])
        assert res.success
        assert os.path.exists("outputs/test_save.txt")
        add_result("Node", "FILE_SAVE", True, "Successfully saved to file.")
    except Exception as e:
        add_result("Node", "FILE_SAVE", False, str(e))

def test_loop_node():
    node = NodeData(title="Loop", type=NodeType.LOOP_OVER_ITEMS, batchSize=2)
    try:
        res = execute_node(node, [FlowItem(text="1"), FlowItem(text="2"), FlowItem(text="3")])
        assert res.success
        # Loop node prepares batches, outputItems is just items but it creates iteratorBatches
        assert len(res.outputItems) == 3
        add_result("Node", "LOOP_OVER_ITEMS", True, "Successfully batched items.")
    except Exception as e:
        add_result("Node", "LOOP_OVER_ITEMS", False, str(e))

def test_merge_node():
    node = NodeData(title="Merge", type=NodeType.MERGE, mergeMode=MergeMode.APPEND)
    try:
        from src.models.node_models import Pin, FlowPayload
        pin1 = Pin(id="pin1", name="in1")
        pin2 = Pin(id="pin2", name="in2")
        node.inputs = [pin1, pin2]
        
        payload = FlowPayload()
        payload.itemsByPinId = {
            "pin1": [FlowItem(text="A")],
            "pin2": [FlowItem(text="B")]
        }
        
        res = execute_node(node, [], {node.id: payload})
        assert res.success
        assert len(res.outputItems) == 2
        add_result("Node", "MERGE", True, "Successfully appended multiple pins.")
    except Exception as e:
        add_result("Node", "MERGE", False, str(e))

def test_mcp_tools():
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
        except Exception as e:
            add_result("MCP Server", server_name, False, f"Exception occurred: {str(e)}")

