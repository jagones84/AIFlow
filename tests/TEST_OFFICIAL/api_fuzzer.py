import os
import json
import asyncio
import uuid
import httpx
import pytest
from typing import List, Dict, Any
from openai import AsyncOpenAI

# Configuration
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

API_BASE_URL = "http://127.0.0.1:8000/api"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class WorkflowFuzzer:
    """
    AI-Driven API Fuzzer.
    Uses an LLM to generate diverse, complex, and potentially edge-case JSON payloads
    representing FlowProjectData. It then fires them at the backend /api/run endpoint
    and evaluates the results.
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.model = "qwen/qwen3.6-35b-a3b" # Default reliable model

    async def generate_fuzz_payload(self, complexity: str = "medium") -> Dict[str, Any]:
        """Ask the LLM to generate a random but valid workflow JSON."""
        
        prompt = f"""You are an automated testing engine for a node-based workflow system.
Your job is to generate a VALID but complex workflow JSON payload to test the backend engine.
Complexity level requested: {complexity}

The JSON MUST conform to this schema:
{{
  "name": "Fuzz Test Workflow",
  "nodes": [
    {{
      "id": "1",
      "type": "TRIGGER",
      "title": "Trigger",
      "position": {{"x": 0, "y": 0}},
      "inputs": [],
      "outputs": [{{"id": "1_out", "name": "output_1", "parentNodeId": "1"}}],
      "config": {{"triggerType": "MANUAL"}}
    }},
    // ... more nodes ...
  ],
  "connections": [
    {{
      "id": "conn_1",
      "fromNodeId": "1",
      "fromPinId": "1_out",
      "toNodeId": "2",
      "toPinId": "2_in"
    }}
  ]
}}

Available Node Types: TRIGGER, AI_AGENT, TOOL_EXECUTION, ROUTER, SWITCH, PROMPT_INPUT, KNOWLEDGE, JSON_PARSER, JSON_FIELD_EXTRACT, MERGE, LOOP_OVER_ITEMS, VARIABLE_STORE, FILE_SAVE, STOP_AND_ERROR, HTTP_REQUEST, WAIT, CODE, SET, FILTER, SORT, LIMIT, AGGREGATE, REMOVE_DUPLICATES, SPLIT_OUT, SUMMARIZE, HTML, EXECUTE_WORKFLOW, OUTPUT_DISPLAY.

CRITICAL REQUIREMENT: For EVERY node configuration you add, use the exact configuration fields as defined in the system. For example, HTTP_REQUEST MUST use `httpUrl`, not `url`. AI_AGENT MUST use `modelId`, not `model`.

Rules:
1. Every workflow MUST start with a TRIGGER node.
2. Ensure `toNodeId` and `fromNodeId` match actual node IDs in the array.
3. Include at least 3 different node types.
4. Output ONLY raw JSON, no markdown formatting, no explanations.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9 # High temperature for diverse fuzzing
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content)

    async def execute_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fire the payload at the backend and wait for completion."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1. Start execution
            start_resp = await client.post(f"{API_BASE_URL}/run", json=payload)
            start_resp.raise_for_status()
            start_data = start_resp.json()
            
            if start_data.get("status") == "error":
                return start_data

            # 2. Poll for results
            for _ in range(120): # Max 1 minute
                await asyncio.sleep(0.5)
                res_resp = await client.get(f"{API_BASE_URL}/results")
                res_data = res_resp.json()
                if not res_data.get("running", False):
                    return res_data
                    
            return {"status": "timeout", "error": "Execution timed out"}

    async def evaluate_results(self, payload: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Use the LLM to evaluate if the execution results make logical sense."""
        if results.get("status") in ["error", "timeout"]:
            print(f"Fuzz test failed immediately: {results.get('error')}")
            return False

        eval_prompt = f"""You are an automated test evaluator. 
Review the following workflow execution results. Determine if the engine behaved correctly based on the input payload.

PAYLOAD (What was requested):
{json.dumps(payload, indent=2)[:3000]}... [truncated]

RESULTS (What the engine did):
{json.dumps(results, indent=2)[:4000]}... [truncated]

Check carefully for:
1. Routing correctness (did nodes trigger the correct downstream nodes?)
2. State management (did LOOP_OVER_ITEMS emit batches properly?)
3. Missing fields (were errors thrown despite valid configuration?)
4. Invalid nodes executing (did disconnected nodes run?)

Did the engine execute this workflow correctly without crashing or producing logically impossible states?
Reply with ONLY 'PASS' or 'FAIL'. If 'FAIL', append a short, specific reason.
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1
        )
        
        evaluation = response.choices[0].message.content.strip()
        print(f"AI Evaluation: {evaluation}")
        return evaluation.startswith("PASS")

async def run_fuzz_batch(iterations: int = 5):
    print(f"Starting Fuzz Batch ({iterations} iterations)...")
    fuzzer = WorkflowFuzzer()
    
    passes = 0
    for i in range(iterations):
        print(f"\n--- Fuzz Iteration {i+1} ---")
        try:
            payload = await fuzzer.generate_fuzz_payload()
            print(f"Generated Payload with {len(payload.get('nodes', []))} nodes.")
            
            results = await fuzzer.execute_payload(payload)
            print(f"Execution Status: {results.get('status')}")
            
            passed = await fuzzer.evaluate_results(payload, results)
            if passed:
                passes += 1
        except Exception as e:
            print(f"Iteration failed with exception: {str(e)}")
            
    print(f"\nBatch Complete: {passes}/{iterations} passed.")
    return passes == iterations

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY must be set in the environment.")
    else:
        asyncio.run(run_fuzz_batch(3))
