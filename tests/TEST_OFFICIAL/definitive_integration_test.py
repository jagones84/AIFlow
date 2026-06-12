import os
import json
import asyncio
import httpx
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

API_BASE_URL = "http://127.0.0.1:8000/api"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class DefinitiveTestEvaluator:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.eval_model = "qwen/qwen3.6-35b-a3b"

    async def run_definitive_test(self) -> bool:
        print("\n--- Definitive App-Like Integration Test ---")
        print("Scenario: A Panel Discussion. Host asks a question -> 2 Panelists answer -> Merge (Wait) -> Host summarizes.")
        
        payload = {
            "name": "Definitive Panel Test",
            "nodes": [
                {
                    "id": "1", "type": "TRIGGER", "title": "Trigger",
                    "outputs": [{"id": "1_out", "name": "output_1"}],
                    "config": {}
                },
                {
                    "id": "2", "type": "PROMPT_INPUT", "title": "Topic Input",
                    "inputs": [{"id": "2_in", "name": "input_1"}],
                    "outputs": [{"id": "2_out", "name": "output_1"}],
                    "config": {"promptText": "What is the best color for a sports car? Ask the panelists."}
                },
                {
                    "id": "3", "type": "AI_AGENT", "title": "Host Question",
                    "inputs": [{"id": "3_in", "name": "input_1"}],
                    "outputs": [{"id": "3_out", "name": "output_1"}],
                    "modelId": "qwen/qwen3.6-35b-a3b",
                    "systemPrompt": "You are a TV Host. Ask the panelists the user's question. Max 10 words.",
                    "config": {}
                },
                {
                    "id": "4", "type": "AI_AGENT", "title": "Panelist 1",
                    "inputs": [{"id": "4_in", "name": "input_1"}],
                    "outputs": [{"id": "4_out", "name": "output_1"}],
                    "modelId": "qwen/qwen3.6-35b-a3b",
                    "systemPrompt": "You are Panelist 1. Say 'Red is the best.' Max 5 words.",
                    "config": {}
                },
                {
                    "id": "5", "type": "AI_AGENT", "title": "Panelist 2",
                    "inputs": [{"id": "5_in", "name": "input_1"}],
                    "outputs": [{"id": "5_out", "name": "output_1"}],
                    "modelId": "qwen/qwen3.6-35b-a3b",
                    "systemPrompt": "You are Panelist 2. Say 'Black is the best.' Max 5 words.",
                    "config": {}
                },
                {
                    "id": "6", "type": "MERGE", "title": "Wait for Panelists",
                    "inputs": [{"id": "6_in1", "name": "input_1"}, {"id": "6_in2", "name": "input_2"}],
                    "outputs": [{"id": "6_out", "name": "output_1"}],
                    "mergeMode": "WAIT",
                    "config": {}
                },
                {
                    "id": "7", "type": "AI_AGENT", "title": "Host Summary",
                    "inputs": [{"id": "7_in", "name": "input_1"}],
                    "outputs": [{"id": "7_out", "name": "output_1"}],
                    "modelId": "qwen/qwen3.6-35b-a3b",
                    "systemPrompt": "You are the TV Host. Summarize the two answers. End your response with exactly the word 'PANEL_CONCLUDED'.",
                    "config": {}
                },
                {
                    "id": "8", "type": "OUTPUT_DISPLAY", "title": "Final Display",
                    "inputs": [{"id": "8_in", "name": "input_1"}],
                    "outputs": [],
                    "config": {}
                }
            ],
            "connections": [
                {"id": "c1", "fromNodeId": "1", "fromPinId": "1_out", "toNodeId": "2", "toPinId": "2_in"},
                {"id": "c2", "fromNodeId": "2", "fromPinId": "2_out", "toNodeId": "3", "toPinId": "3_in"},
                
                # Host asks both panelists
                {"id": "c3", "fromNodeId": "3", "fromPinId": "3_out", "toNodeId": "4", "toPinId": "4_in"},
                {"id": "c4", "fromNodeId": "3", "fromPinId": "3_out", "toNodeId": "5", "toPinId": "5_in"},
                
                # Panelists answer and merge waits
                {"id": "c5", "fromNodeId": "4", "fromPinId": "4_out", "toNodeId": "6", "toPinId": "6_in1"},
                {"id": "c6", "fromNodeId": "5", "fromPinId": "5_out", "toNodeId": "6", "toPinId": "6_in2"},
                
                # Merge goes to Host Summary
                {"id": "c7", "fromNodeId": "6", "fromPinId": "6_out", "toNodeId": "7", "toPinId": "7_in"},
                
                # Summary goes to Display
                {"id": "c8", "fromNodeId": "7", "fromPinId": "7_out", "toNodeId": "8", "toPinId": "8_in"}
            ]
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{API_BASE_URL}/run", json=payload)
            if resp.status_code != 200:
                print("Failed to start definitive flow")
                return False
                
            print("Flow started. Waiting for execution to complete (can take 30-60s for multiple AI turns)...")
            
            for _ in range(360): # Up to 3 mins
                await asyncio.sleep(1.0)
                try:
                    res_resp = await client.get(f"{API_BASE_URL}/results", timeout=5.0)
                    res_data = res_resp.json()
                    if not res_data.get("running", True):
                        print("Flow has finished running.")
                        break
                except Exception as e:
                    print(f"Polling error: {e}")
                    pass
            
            res_data = res_resp.json()
            results = res_data.get("results", [])
            
            # Extract Output
            agent_output = ""
            for r in results:
                if r.get("id") == "7":
                    agent_output = r.get("lastOutput") or ""
            
            print(f"\n[Host Final Summary Output]:\n{agent_output}\n")
            
            # Semantic / Syntax Evaluation
            if "PANEL_CONCLUDED" in agent_output:
                print("✅ Syntax check passed: 'PANEL_CONCLUDED' found.")
            else:
                print("❌ Syntax check failed: 'PANEL_CONCLUDED' missing.")
                return False
                
            # Quality Evaluation via LLM Judge
            eval_prompt = f"""You are evaluating the quality of an AI agent discussion flow.
Two panelists were asked about the best color for a sports car. Panelist 1 was instructed to say Red. Panelist 2 was instructed to say Black.
The Host was supposed to summarize their answers.
Here is the Host's summary:
"{agent_output}"

Does this summary accurately reflect that the panelists chose Red and Black?
Reply with ONLY 'PASS' or 'FAIL'.
"""
            eval_resp = await self.client.chat.completions.create(
                model=self.eval_model,
                messages=[{"role": "user", "content": eval_prompt}],
                temperature=0.1
            )
            
            evaluation = eval_resp.choices[0].message.content.strip()
            print(f"AI Quality Evaluation: {evaluation}")
            return evaluation.startswith("PASS")

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY must be set in the environment.")
    else:
        evaluator = DefinitiveTestEvaluator()
        success = asyncio.run(evaluator.run_definitive_test())
        if success:
            print("\n🎉 DEFINITIVE TEST PASSED - FULL WORKFLOW LOGIC AND QUALITY VERIFIED!")
        else:
            print("\n💀 DEFINITIVE TEST FAILED")