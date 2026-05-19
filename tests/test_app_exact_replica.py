#!/usr/bin/env python3
"""
Test that exactly replicates the app environment.
"""
import os
import sys

# Add parent directory to path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This is exactly what server.py does
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

print("=" * 60)
print("Environment Check")
print("=" * 60)
print(f"OPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY', 'NOT SET')[:30]}...")
print(f"BRAVE_API_KEY: {os.getenv('BRAVE_API_KEY', 'NOT SET')[:20]}...")

# Now import what the app imports
from src.models.node_models import FlowProjectData, NodeData, NodeType, FlowItem
from src.main import FlowApp
import asyncio

# Create a simple workflow matching the app's structure
nodes = [
    NodeData(id="trigger_1", title="Trigger", type=NodeType.TRIGGER),
    NodeData(id="user_input_1", title="USER_INPUT", type=NodeType.USER_INPUT),
    NodeData(id="ai_agent_1", title="AI_AGENT", type=NodeType.AI_AGENT, 
             modelId="qwen/qwen3.6-35b-a3b",
             allowedTools=["fetch_url", "mcp__Brave Search", "mcp__Multi-Fetch"]),
]

# Create project
project = FlowProjectData(name="Test", nodes=nodes, connections=[])

print("\n" + "=" * 60)
print("Starting Flow (exactly like app does)")
print("=" * 60)

app = FlowApp(project)

async def run_test():
    await app.orchestrator.start_flow()
    
    # Wait for completion (like server.py does)
    import time
    timeout = 120
    start_time = time.time()
    
    while app.orchestrator.is_flow_running and time.time() - start_time < timeout:
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("Execution Logs")
    print("=" * 60)
    for log in app.orchestrator.execution_logs:
        print(log)
    
    print("\n" + "=" * 60)
    print("Node Results")
    print("=" * 60)
    for node in app.get_nodes():
        print(f"Node: {node.title} [{node.type.value}]")
        print(f"  Status: {node.status.value}")
        print(f"  Output: {node.lastOutput[:200] if node.lastOutput else 'None'}...")

asyncio.run(run_test())
