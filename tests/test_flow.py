import asyncio
import pytest
from src.models.node_models import FlowProjectData, NodeData, Connection, NodeType, Pin, SetFieldDefinition, NodeStatus, FlowItem, MergeMode
from src.main import FlowApp
from src.logic.node_executor import NodeExecutor

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


def test_merge_append_produces_single_combined_item_with_sources():
    merge_in_1 = Pin(name="input_1")
    merge_in_2 = Pin(name="input_2")
    merge_out = Pin(name="output_1")
    merge_node = NodeData(
        title="Merge",
        type=NodeType.MERGE,
        inputs=[merge_in_1, merge_in_2],
        outputs=[merge_out],
        mergeMode=MergeMode.APPEND,
    )

    items = [
        FlowItem(json_data={"text": "Answer from medical researcher", "_sourceNodeTitle": "Medical Researcher"}),
        FlowItem(json_data={"text": "Answer from psychologist", "_sourceNodeTitle": "Psychologist"}),
    ]

    executor = NodeExecutor()
    result = executor.execute(merge_node, items, [merge_node], {}, None, None)

    assert result.success is True
    assert len(result.outputItems) == 1
    merged_text = result.outputItems[0].json_data.get("text", "")
    assert "### Medical Researcher" in merged_text
    assert "Answer from medical researcher" in merged_text
    assert "### Psychologist" in merged_text
    assert "Answer from psychologist" in merged_text


def test_ai_agent_memory_persists_across_iterations_without_provider_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    ai_in = Pin(name="input_1")
    ai_out = Pin(name="output_1")
    node = NodeData(
        title="Agent",
        type=NodeType.AI_AGENT,
        inputs=[ai_in],
        outputs=[ai_out],
        modelId="qwen/qwen3.6-35b-a3b",
        systemPrompt="You are a helpful assistant.",
        allowedTools=[],
    )

    executor = NodeExecutor()

    r1 = executor.execute(node, [FlowItem(json_data={"text": "Hello"})], [node], {}, None, None)
    assert r1.updatedNode is not None
    h1 = r1.updatedNode.context.get("chat_history", [])
    assert isinstance(h1, list)
    assert len(h1) == 2

    r2 = executor.execute(r1.updatedNode, [FlowItem(json_data={"text": "Second turn"})], [r1.updatedNode], {}, None, None)
    assert r2.updatedNode is not None
    h2 = r2.updatedNode.context.get("chat_history", [])
    assert isinstance(h2, list)
    assert len(h2) == 4
