import asyncio
import os
import sys
import json
import requests
from dotenv import load_dotenv
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

pytestmark = pytest.mark.integration


def test_architect_api():
    base_url = "http://localhost:8000/api/architect"

    print("--- 1. Testing Manual Graph API ---")
    print("Clearing project...")
    res = requests.post(f"{base_url}/action", json={"action": "ClearProject", "params": {}})
    print(res.json())

    print("\nAdding TRIGGER node...")
    res = requests.post(f"{base_url}/action", json={"action": "AddNode", "params": {"type": "TRIGGER", "title": "Start", "x": 100, "y": 200}})
    n1_id = res.json()["node_id"]

    print("Adding HTTP_REQUEST node...")
    res = requests.post(f"{base_url}/action", json={"action": "AddNode", "params": {"type": "HTTP_REQUEST", "title": "Fetch Data", "x": 400, "y": 200}})
    n2_id = res.json()["node_id"]

    print("Connecting nodes...")
    res = requests.post(f"{base_url}/action", json={"action": "ConnectNodes", "params": {"fromNode": n1_id, "toNode": n2_id}})     

    print("Getting current graph...")
    res = requests.get(f"{base_url}/graph")
    graph = res.json()
    print(f"Graph nodes: {len(graph['nodes'])}, connections: {len(graph['connections'])}")
    
    print("\n--- 2. Testing AI Architect Endpoint ---")
    payload = {
        "prompt": "Create a flow that triggers, gets user input, passes it to an AI_AGENT with Brave Search, and saves to file.",
        "model": "google/gemini-3.1-flash-lite"
    }
    print("Sending complex prompt to Architect AI... (This will take 5-15 seconds as it loops)")
    
    # We do a quick poll in a separate thread just to see the status changing
    import threading
    import time
    
    done = False
    def poll_status():
        last = ""
        while not done:
            try:
                r = requests.get(f"{base_url}/graph")
                status = r.json().get("last_action", "")
                if status != last:
                    print(f"  [Poller] Agent status: {status}")
                    last = status
            except:
                pass
            time.sleep(1)
            
    t = threading.Thread(target=poll_status)
    t.start()
    
    try:
        res = requests.post(base_url, json=payload)
        result = res.json()
        print("\n--- ARCHITECT RESULT ---")
        print(f"Status: {result.get('status')}")
        if result.get("drawflow"):
            data = result["drawflow"]["drawflow"]["Home"]["data"]
            print(f"Generated Nodes: {len(data)}")
            for k,v in data.items():
                print(f"  - {v['name']} (ID: {v['id']})")
        else:
            print(f"Error Message: {result.get('message')}")
    finally:
        done = True
        t.join()

if __name__ == "__main__":
    test_architect_api()
