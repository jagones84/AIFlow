import asyncio
import os
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from src.logic.node_executor import NodeExecutor
from src.models.node_models import Node, Position

async def test_ai_hallucination():
    executor = NodeExecutor()
    
    # We create a fake node for AI
    ai_node = Node(
        id="node_1",
        name="AI_AGENT",
        type="AI_AGENT",
        position=Position(x=0, y=0),
        data={
            "prompt": "You are a helpful AI.",
            "model": "x-ai/grok-4.1-fast",
            "provider": "openrouter"
        },
        allowedTools=["mcp__brave_search", "mcp__multi_fetch"]
    )
    
    inputs = {"input": "latest soccer italian match with result, search for it. Today is 14 May 2026."}
    
    print("Executing AI Agent...")
    result = await executor.execute(ai_node, inputs)
    
    print("\n--- RESULTS ---")
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    if result.error:
         print(f"Error: {result.error}")
    
if __name__ == "__main__":
    asyncio.run(test_ai_hallucination())
