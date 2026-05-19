#!/usr/bin/env python3
"""
Test that exactly replicates the app's /api/run call.
This simulates what happens when the browser sends project data to the server.
"""
import os
import sys
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

print("=" * 60)
print("Testing exact app behavior - /api/run simulation")
print("=" * 60)
print(f"OPENROUTER_API_KEY: {'SET' if os.getenv('OPENROUTER_API_KEY') else 'NOT SET'}")
print(f"BRAVE_API_KEY: {'SET' if os.getenv('BRAVE_API_KEY') else 'NOT SET'}")

from src.models.node_models import FlowProjectData, NodeData, NodeType, Connection
from src.logic.node_executor import NodeExecutor
from src.logic.flow_orchestrator import FlowOrchestrator
from src.utils.managers import LogManager

class FlowApp:
    def __init__(self, project_data: FlowProjectData):
        self.project_data = project_data
        
        self.node_executor = NodeExecutor()
        
        def get_nodes():
            return self.project_data.nodes
        def get_connections():
            return self.project_data.connections
        def update_nodes(nodes):
            self.project_data.nodes = nodes
        def update_connections(connections):
            self.project_data.connections = connections
        def load_flow(flow_id):
            return None
            
        self.orchestrator = FlowOrchestrator(
            node_executor=self.node_executor,
            get_nodes=get_nodes,
            get_connections=get_connections,
            update_nodes=update_nodes,
            update_connections=update_connections,
            load_flow=load_flow
        )

def create_test_project():
    """Create a project identical to what the app sends"""
    trigger = NodeData(
        id="trigger_1",
        title="Trigger",
        type=NodeType.TRIGGER,
        triggerType="MANUAL"
    )
    
    user_input = NodeData(
        id="user_input_1", 
        title="USER_INPUT",
        type=NodeType.USER_INPUT
    )
    
    ai_agent = NodeData(
        id="ai_agent_1",
        title="AI_AGENT",
        type=NodeType.AI_AGENT,
        modelId="qwen/qwen3.6-35b-a3b",
        allowedTools=["fetch_url", "mcp__Brave Search"],
        systemPrompt="You are a helpful assistant."
    )
    
    conn1 = Connection(fromNodeId="trigger_1", fromPinId="output_1", toNodeId="user_input_1", toPinId="input_1")
    conn2 = Connection(fromNodeId="user_input_1", fromPinId="output_1", toNodeId="ai_agent_1", toPinId="input_1")
    
    return FlowProjectData(
        name="Test",
        nodes=[trigger, user_input, ai_agent],
        connections=[conn1, conn2]
    )

async def run_flow():
    project = create_test_project()
    print(f"\nCreated project with {len(project.nodes)} nodes and {len(project.connections)} connections")
    
    app = FlowApp(project)
    
    await app.orchestrator.start_flow()
    
    import time
    timeout = 120
    start_time = time.time()
    
    while app.orchestrator.is_flow_running and time.time() - start_time < timeout:
        await asyncio.sleep(0.5)
        if int(time.time() - start_time) % 5 == 0:
            print(f"  ...still running after {int(time.time() - start_time)}s...")
    
    print(f"\n{'='*60}")
    print("EXECUTION LOGS")
    print("="*60)
    for log in app.orchestrator.execution_logs:
        print(log)
    
    print(f"\n{'='*60}")
    print("NODE RESULTS")
    print("="*60)
    for node in app.get_nodes():
        print(f"\nNode: {node.title} [{node.type.value}]")
        print(f"  Status: {node.status.value}")
        output = node.lastOutput or "None"
        print(f"  Output: {output[:300]}..." if len(output) > 300 else f"  Output: {output}")
        if node.lastOutputItems:
            print(f"  Output Items: {len(node.lastOutputItems)}")
            for item in node.lastOutputItems[:2]:
                text = item.json_data.get("text", str(item.json_data))
                print(f"    - {text[:150]}...")

if __name__ == "__main__":
    try:
        asyncio.run(run_flow())
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
