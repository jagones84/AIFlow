import asyncio
import pytest
from src.models.node_models import FlowProjectData, NodeData, Connection, NodeType, Pin, SetFieldDefinition, NodeStatus
from src.main import FlowApp

@pytest.mark.asyncio
async def test_simple_flow():
    # Create a trigger node
    trigger_out = Pin(name="output")
    trigger = NodeData(
        title="Start",
        type=NodeType.TRIGGER,
        outputs=[trigger_out]
    )

    # Create a Set node
    set_in = Pin(name="input")
    set_out = Pin(name="output")
    set_node = NodeData(
        title="Set Data",
        type=NodeType.SET,
        inputs=[set_in],
        outputs=[set_out],
        setFields=[
            SetFieldDefinition(name="message", value="Hello World", type="string"),
            SetFieldDefinition(name="count", value="42", type="number")
        ]
    )

    # Create a Filter node
    filter_in = Pin(name="input")
    filter_out_true = Pin(name="True")
    filter_out_false = Pin(name="False")
    filter_node = NodeData(
        title="Filter",
        type=NodeType.ROUTER, # We use ROUTER for simple boolean filters
        routerMode="SIMPLE_RULE",
        ruleCondition="expr: {{ $json.count }} == 42",
        inputs=[filter_in],
        outputs=[filter_out_true, filter_out_false]
    )

    # Connections
    conn1 = Connection(fromNodeId=trigger.id, fromPinId=trigger_out.id, toNodeId=set_node.id, toPinId=set_in.id)
    conn2 = Connection(fromNodeId=set_node.id, fromPinId=set_out.id, toNodeId=filter_node.id, toPinId=filter_in.id)

    project = FlowProjectData(
        name="Test Project",
        nodes=[trigger, set_node, filter_node],
        connections=[conn1, conn2]
    )

    app = FlowApp(project)
    await app.run()
    app.orchestrator.stop_flow()

    nodes = app.get_nodes()
    
    # Assertions
    assert len(nodes) == 3
    for n in nodes:
        assert n.status == NodeStatus.SUCCESS, f"Node {n.title} failed with output {n.lastOutput}"
        
    final_node = next(n for n in nodes if n.title == "Filter")
    assert len(final_node.lastOutputItems) == 1
    assert final_node.lastOutputItems[0].json_data.get("message") == "Hello World"
    assert final_node.lastOutputItems[0].json_data.get("count") == 42
