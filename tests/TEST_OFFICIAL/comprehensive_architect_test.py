import os
import json
import asyncio
import httpx
from typing import Dict, Any, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

API_BASE_URL = "http://127.0.0.1:8000/api"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class ComprehensiveTestEvaluator:
    """
    Executes a comprehensive AI-driven test of the engine, ensuring that all major node types
    (TRIGGER, KNOWLEDGE, ROUTER, AI_AGENT, HTTP_REQUEST) integrate properly.
    It also tests the Architect Agent's ability to generate valid graphs.
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.eval_model = "qwen/qwen3.6-35b-a3b"

    async def test_architect_agent(self) -> bool:
        print("\n--- Test 2: Architect Agent Batch Test ---")
        prompt = "Create a workflow that starts manually, fetches weather data from an API, routes the result based on temperature, and uses an AI agent to summarize the output."
        print(f"Asking Architect to: {prompt}")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{API_BASE_URL}/architect", json={"prompt": prompt})
            if resp.status_code != 200:
                print(f"Architect API failed: {resp.status_code}")
                return False
                
            data = resp.json()
            if data.get("status") != "running":
                print(f"Architect returned error: {data}")
                return False
                
            # Poll for architect completion
            for _ in range(120): # Max 1 minute
                await asyncio.sleep(0.5)
                res_resp = await client.get(f"{API_BASE_URL}/architect/results")
                res_data = res_resp.json()
                if not res_data.get("running", True):
                    break
            
            # Now get the graph
            graph_resp = await client.get(f"{API_BASE_URL}/architect/graph")
            graph = graph_resp.json()
            nodes = graph.get("nodes", [])
            
            # Evaluate the graph using LLM
            eval_prompt = f"""You are evaluating an AI Architect that builds workflows.
User asked: "{prompt}"
Architect produced these nodes:
{json.dumps([{'type': n.get('type'), 'title': n.get('title')} for n in nodes], indent=2)}

Does this workflow graph logically satisfy the user's request? (It must have TRIGGER, HTTP_REQUEST, ROUTER/SWITCH, and AI_AGENT/SUMMARIZE).
Reply with ONLY 'PASS' or 'FAIL'. If 'FAIL', append a reason.
"""
            eval_resp = await self.client.chat.completions.create(
                model=self.eval_model,
                messages=[{"role": "user", "content": eval_prompt}],
                temperature=0.1
            )
            
            evaluation = eval_resp.choices[0].message.content.strip()
            print(f"Architect Graph Evaluation: {evaluation}")
            return evaluation.startswith("PASS")

    async def test_comprehensive_integration(self) -> bool:
        print("\n--- Test 3: Comprehensive Node Integration Test ---")
        payload = {
            "name": "Integration Test",
            "nodes": [
                {"id": "1", "type": "TRIGGER", "title": "Trigger", "config": {}},
                {"id": "2", "type": "HTTP_REQUEST", "title": "Fetch Data", "httpUrl": "https://dummyjson.com/users/1", "httpMethod": "GET", "config": {}},
                {"id": "3", "type": "SET", "title": "Set Data", "setFields": [{"name": "test_marker", "value": "Valid", "type": "string"}], "keepOnlySetFields": False, "config": {}},
                {"id": "4", "type": "AI_AGENT", "title": "Agent", "modelId": "qwen/qwen3.6-35b-a3b", "systemPrompt": "You are a test bot. Look at the input JSON. If 'firstName' is 'Emily' and 'test_marker' is 'Valid', output exactly the word 'INTEGRATION_SUCCESS' and nothing else.", "config": {}},
                {"id": "5", "type": "OUTPUT_DISPLAY", "title": "Output", "config": {}}
            ],
            "connections": [
                {"id": "c1", "fromNodeId": "1", "fromPinId": "out", "toNodeId": "2", "toPinId": "in"},
                {"id": "c2", "fromNodeId": "2", "fromPinId": "out", "toNodeId": "3", "toPinId": "in"},
                {"id": "c3", "fromNodeId": "3", "fromPinId": "out", "toNodeId": "4", "toPinId": "in"},
                {"id": "c4", "fromNodeId": "4", "fromPinId": "out", "toNodeId": "5", "toPinId": "in"}
            ]
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{API_BASE_URL}/run", json=payload)
            if resp.status_code != 200:
                print("Failed to start integration flow")
                return False
                
            for _ in range(120):
                await asyncio.sleep(0.5)
                try:
                    res_resp = await client.get(f"{API_BASE_URL}/results", timeout=5.0)
                    res_data = res_resp.json()
                    if not res_data.get("running", True):
                        break
                except:
                    pass
            
            res_data = res_resp.json()
            results = res_data.get("results", [])
            
            # Extract Output
            agent_output = ""
            for r in results:
                if r.get("id") == "4":
                    agent_output = r.get("lastOutput", "")
            
            print(f"Agent Output: {agent_output}")
            
            if "INTEGRATION_SUCCESS" in agent_output.strip():
                return True
            else:
                print("Agent did not output INTEGRATION_SUCCESS.")
                return False

async def run_all_tests():
    print("Starting Comprehensive Architect & Integration Tests...")
    evaluator = ComprehensiveTestEvaluator()
    
    # Test 2: Architect Batch Generation
    passed_architect = await evaluator.test_architect_agent()
    if passed_architect:
        print("✅ Test 2 PASSED")
    else:
        print("❌ Test 2 FAILED")

    # Test 3: Comprehensive Node Integration
    passed_integration = await evaluator.test_comprehensive_integration()
    if passed_integration:
        print("✅ Test 3 PASSED")
    else:
        print("❌ Test 3 FAILED")

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY must be set in the environment.")
    else:
        asyncio.run(run_all_tests())
