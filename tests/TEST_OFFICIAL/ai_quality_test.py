import os
import json
import asyncio
import httpx
from typing import Dict, Any
from openai import AsyncOpenAI

# Configuration
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

API_BASE_URL = "http://127.0.0.1:8000/api"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class AgentQualityEvaluator:
    """
    AI-Agent Quality Evaluation Test
    This test runs specific workflows that utilize the AI_AGENT node to verify that
    not only does the workflow execute, but the LLM output is coherent, concise,
    and logically correct with respect to the input.
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.eval_model = "qwen/qwen3.6-35b-a3b"

    async def run_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fire the payload at the backend and wait for completion."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            start_resp = await client.post(f"{API_BASE_URL}/run", json=payload)
            start_resp.raise_for_status()
            start_data = start_resp.json()
            
            if start_data.get("status") == "error":
                return start_data

            # Let the backend initialize
            await asyncio.sleep(2.0)

            for _ in range(360): # Max 3 minutes
                await asyncio.sleep(0.5)
                try:
                    res_resp = await client.get(f"{API_BASE_URL}/results", timeout=5.0)
                    res_resp.raise_for_status()
                    res_data = res_resp.json()
                    if not res_data.get("running", True):
                        return res_data
                except Exception as e:
                    print(f"Error getting results: {e}")
                    # If the server is actually down, we should break
                    # But if it's just a read timeout, we can continue
                    if "ConnectError" in str(type(e)):
                        return {"status": "error", "error": f"Connection error: {e}"}
                    
            return {"status": "timeout", "error": "Execution timed out"}

    async def evaluate_coherence(self, user_prompt: str, system_prompt: str, ai_output: str) -> bool:
        """Use an LLM to evaluate if the AI_AGENT's response is coherent and concise."""
        eval_prompt = f"""You are a strict QA evaluator for an AI Agent framework.
Review the following interaction to ensure the AI Agent followed instructions, 
remained concise, and provided a coherent response.

[System Prompt Given to Agent]:
{system_prompt}

[User Input Given to Agent]:
{user_prompt}

[Agent's Output]:
{ai_output}

EVALUATION CRITERIA:
1. Coherence: Does the output logically answer the user's input?
2. Conciseness: Is the output reasonably brief? (Agents in this test are instructed to be extremely concise to save tokens).
3. Instruction Following: Did it obey the system prompt constraints?

Reply with ONLY 'PASS' or 'FAIL'. If 'FAIL', append a short reason.
"""
        response = await self.client.chat.completions.create(
            model=self.eval_model,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1
        )
        
        evaluation = response.choices[0].message.content.strip()
        print(f"Quality Evaluation: {evaluation}")
        return evaluation.startswith("PASS")

    def create_math_reasoning_payload(self):
        """Creates a simple workflow with a concise AI agent."""
        return {
          "name": "Math Reasoning Test",
          "nodes": [
            {
              "id": "1",
              "type": "TRIGGER",
              "title": "Trigger",
              "config": {"triggerType": "MANUAL"},
              "inputs": [],
              "outputs": [{"id": "1_out", "name": "output_1", "parentNodeId": "1"}]
            },
            {
              "id": "2",
              "type": "PROMPT_INPUT",
              "title": "Prompt",
              "config": {"promptText": "If I have 5 apples and give away 2, then buy 4 more, how many do I have?"},
              "inputs": [{"id": "2_in", "name": "input_1", "parentNodeId": "2"}],
              "outputs": [{"id": "2_out", "name": "output_1", "parentNodeId": "2"}]
            },
            {
              "id": "3",
              "type": "AI_AGENT",
              "title": "Concise Agent",
              "modelId": "qwen/qwen3.6-35b-a3b",
              "systemPrompt": "You are a math assistant. You MUST be extremely concise. Provide only the final number and a 1-sentence explanation to save tokens.",
              "config": {
                  "modelId": "qwen/qwen3.6-35b-a3b",
                  "systemPrompt": "You are a math assistant. You MUST be extremely concise. Provide only the final number and a 1-sentence explanation to save tokens."
              },
              "inputs": [{"id": "3_in", "name": "input_1", "parentNodeId": "3"}],
              "outputs": [{"id": "3_out", "name": "output_1", "parentNodeId": "3"}]
            }
          ],
          "connections": [
            {"id": "c1", "fromNodeId": "1", "fromPinId": "1_out", "toNodeId": "2", "toPinId": "2_in"},
            {"id": "c2", "fromNodeId": "2", "fromPinId": "2_out", "toNodeId": "3", "toPinId": "3_in"}
          ]
        }

async def run_quality_tests():
    print("Starting AI-Agent Quality Evaluation...")
    evaluator = AgentQualityEvaluator()
    
    # Test 1: Math Reasoning & Conciseness
    print("\n--- Test 1: Math Reasoning & Conciseness ---")
    payload = evaluator.create_math_reasoning_payload()
    results = await evaluator.run_workflow(payload)
    
    if results.get("status") in ["error", "timeout"]:
        print(f"Test Failed during execution: {results.get('error')}")
        return
        
    # Extract AI Agent Output
    agent_node = next((n for n in results.get("results", []) if n.get("id") == "3"), None)
    if not agent_node or not agent_node.get("lastOutput"):
        print("Test Failed: Could not extract AI Agent output.")
        return
        
    ai_output = agent_node["lastOutput"]
    print(f"\n[Agent Output]:\n{ai_output}\n")
    
    passed = await evaluator.evaluate_coherence(
        user_prompt="If I have 5 apples and give away 2, then buy 4 more, how many do I have?",
        system_prompt="You are a math assistant. You MUST be extremely concise. Provide only the final number and a 1-sentence explanation to save tokens.",
        ai_output=ai_output
    )
    
    if passed:
        print("✅ Test 1 PASSED")
    else:
        print("❌ Test 1 FAILED")

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY must be set in the environment.")
    else:
        asyncio.run(run_quality_tests())
