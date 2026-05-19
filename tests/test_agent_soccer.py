import asyncio
import os
import sys
from dotenv import load_dotenv
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.logic.node_executor import NodeExecutor
from src.models.node_models import NodeData, NodeType, FlowPayload, FlowItem

pytestmark = pytest.mark.integration


def test_agent_soccer():
    executor = NodeExecutor()
    
    ai_node = NodeData(
        id="node_1",
        title="AI_AGENT",
        type=NodeType.AI_AGENT,
        position={"x":0, "y":0},
        systemPrompt="You are a helpful AI. Answer the user's prompt by using the provided tools. Be concise.",
        modelId="qwen/qwen3.6-35b-a3b",
        allowedTools=[
            "mcp__Brave Search",
            "mcp__Multi-Fetch"
        ]
    )
    
    inputs = {
        "input": "latest soccer italian match with result, search for it"
    }
    
    print("Executing AI Agent for soccer query...")
    payload = FlowPayload.from_items([FlowItem(json={"text": inputs["input"]})])
    result = executor.execute(ai_node, payload.all_items(), [ai_node], {ai_node.id: payload})
    
    print("\n--- RESULTS ---")
    print(f"Success: {result.success}")
    if result.outputItems:
        print(f"Output:\n{result.outputItems[0].json_data.get('text') if result.outputItems else 'No output'}")
    if not result.success:
         print(f"Error: {result.output}")
    
if __name__ == "__main__":
    test_agent_soccer()
