#!/usr/bin/env python3
"""
Test that exactly replicates app behavior:
- Agent with default tools (fetch_url, Brave Search)
- Query: "info sull'ultima partita di Serie A giocata in Italia"
- Verify: tool call works AND agent elaborates on results
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

print("=" * 70)
print("TEST: Serie A Calcio - Agent Tool Usage")
print("=" * 70)

from src.logic.node_executor import NodeExecutor
from src.models.node_models import FlowItem, FlowPayload, NodeData, NodeType

executor = NodeExecutor()
node = NodeData(
    title="AI_AGENT",
    type=NodeType.AI_AGENT,
    modelId="qwen/qwen3.6-35b-a3b",
    allowedTools=["fetch_url", "mcp__Brave Search", "mcp__Multi-Fetch"],
)

payload = FlowPayload.from_items([
    FlowItem(json={"text": "Cercami informazioni sull'ultima partita di Serie A giocata in Italia, con il risultato e i marcatori."})
])

print(f"\n1. EXECUTING AGENT with query:")
print(f"   '{payload.all_items()[0].json_data.get('text', '')}'")
print(f"\n2. Tools available: {node.allowedTools}")

result = executor.execute(
    node, 
    payload.all_items(), 
    [node], 
    {node.id: payload}
)

print(f"\n3. EXECUTION RESULT:")
print(f"   Success: {result.success}")
print(f"   Output: {result.output}")
print(f"   Output Items: {len(result.outputItems) if result.outputItems else 0}")

# Verify the output contains meaningful content
print(f"\n4. VERIFICATION:")

if result.success and result.output:
    # Check if output is not just tool results raw
    output_lower = result.output.lower()
    
    checks = {
        "has_text_response": len(result.output) > 50,
        "not_just_tool_result": not (result.output.startswith("Tool results:") and "\n[brave" in result.output),
        "mentions_calcio": "calcio" in output_lower or "partita" in output_lower or "serie" in output_lower or "goal" in output_lower or "risultato" in output_lower,
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}: {passed}")
    
    all_passed = all(checks.values())
    print(f"\n5. FINAL RESULT: {'✅ TEST PASSED - Agent elaborates correctly!' if all_passed else '❌ TEST FAILED - Agent not elaborating properly'}")
    
    if not all_passed:
        print(f"\n   ISSUE DETECTED:")
        if checks.get("not_just_tool_result") == False:
            print(f"   - Agent returns raw tool results instead of elaborating")
        print(f"\n   Raw output preview:\n   {result.output[:500]}...")
        
else:
    print("❌ Execution failed or no output")

print("\n" + "=" * 70)
