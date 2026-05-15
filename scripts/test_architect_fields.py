import os
import sys
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server import app, current_architect_graph

client = TestClient(app)

def test_architect_update_all_fields():
    # 1. Clear project
    client.post("/api/architect/action", json={"action": "ClearProject", "params": {}})
    
    # 2. Create nodes of different types to test field assignments
    nodes_to_test = [
        {"type": "USER_INPUT", "config": {"userInstruction": "Test Instruction", "isInteractive": True}},
        {"type": "FILTER", "config": {"ruleCondition": "expr:{{ $json.id }} == 1"}},
        {"type": "SORT", "config": {"sortFieldName": "price", "sortOrder": "desc"}},
        {"type": "SET", "config": {"setFields": [{"name": "key1", "value": "val1", "type": "string"}]}},
        {"type": "HTTP_REQUEST", "config": {"httpUrl": "https://test.com", "httpMethod": "POST"}}
    ]
    
    for idx, n in enumerate(nodes_to_test):
        node_id = str(idx + 1)
        # Add node
        client.post("/api/architect/action", json={
            "action": "AddNode", 
            "params": {"id": node_id, "type": n["type"]}
        })
        
        # Update node with complex config
        resp = client.post("/api/architect/action", json={
            "action": "UpdateNode",
            "params": {"id": node_id, "config": n["config"]}
        })
        
        assert resp.json()["status"] == "success"
        
    # Verify the graph structure was updated correctly at the root level and config level
    graph = client.get("/api/architect/graph").json()
    
    print("--- Graph Verification ---")
    for n in graph["nodes"]:
        print(f"Node {n['id']} ({n['type']}):")
        print(f"  Full Node Dict: {n}")
        print(f"  Config object: {n.get('config')}")
        
        # Check if top-level fields were synced correctly
        expected_config = nodes_to_test[int(n['id'])-1]["config"]
        for key, expected_val in expected_config.items():
            actual_val = n.get(key)
            if actual_val == expected_val:
                print(f"  [SUCCESS] Field '{key}' properly synced to root level: {actual_val}")
            else:
                print(f"  [ERROR] Field '{key}' NOT synced correctly. Expected: {expected_val}, Got: {actual_val}")
                
if __name__ == "__main__":
    test_architect_update_all_fields()