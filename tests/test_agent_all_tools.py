import asyncio
import os
import sys
from dotenv import load_dotenv
import pytest

# Add parent dir to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.logic.node_executor import NodeExecutor
from src.models.node_models import NodeData, NodeType

pytestmark = pytest.mark.integration


def test_agent_tools_comprehensive():
    executor = NodeExecutor()
    
    # We create a fake node for AI with multiple MCP tools
    ai_node = NodeData(
        id="node_1",
        title="AI_AGENT",
        type=NodeType.AI_AGENT,
        position={"x":0, "y":0},
        systemPrompt="You are a helpful AI. Answer the user's prompt by using the provided tools. Be concise.",
        modelId="x-ai/grok-4.1-fast",
        allowedTools=[
            "mcp__Docker",
            "mcp__Fetch",
            "mcp__mcp-reasoner",
            "mcp__python-local",
            "mcp__ucpf"
        ]
    )
    
    inputs = {
        "input": """I need you to test every single tool you have access to. You have 5 tools. 
You MUST use AT LEAST ONE method from EVERY single tool you have access to. 
For tools like 'Docker', 'Fetch', 'ucpf', 'mcp-reasoner', just call any basic discovery or read method (like getting status, listing items, or basic evaluation).
For 'python-local', execute a simple print('hello').
Report a numbered summary of the result of all 5 tool executions."""
    }
    
    print("Executing AI Agent with multiple tools...")
    from src.models.node_models import FlowPayload, FlowItem
    payload = FlowPayload.from_items([FlowItem(json={"text": inputs["input"]})])
    result = executor.execute(ai_node, payload.all_items(), [ai_node], {ai_node.id: payload})
    
    print("\n--- RESULTS ---")
    print(f"Success: {result.success}")
    if result.outputItems:
        print(f"Output:\n{result.outputItems[0].json_data.get('text') if result.outputItems else 'No output'}")
    if not result.success:
         print(f"Error: {result.output}")
    
if __name__ == "__main__":
    test_agent_tools_comprehensive()
