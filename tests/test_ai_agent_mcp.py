import json
import os

import pytest
from dotenv import load_dotenv

from src.logic.tools import ToolRegistry


pytestmark = pytest.mark.integration


def test_openrouter_with_mcp_tool_call_roundtrip():
    if os.getenv("RUN_MCP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_MCP_INTEGRATION_TESTS=1 to run MCP integration tests")

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    server_name = "Brave Search"
    mcp_tools = ToolRegistry.get_mcp_server_tools(server_name)
    if not mcp_tools:
        pytest.skip(f"Unable to start MCP server '{server_name}' in this environment")

    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    safe_name = "brave_web_search"
    tool_schema = next((t for t in mcp_tools if t["name"] == safe_name), None)
    if not tool_schema:
        pytest.skip(f"MCP tool '{safe_name}' not available on server '{server_name}'")

    ai_tools = [
        {
            "type": "function",
            "function": {
                "name": safe_name,
                "description": tool_schema.get("description", "Search web"),
                "parameters": tool_schema.get("inputSchema", {"type": "object", "properties": {"query": {"type": "string"}}}),
            },
        }
    ]

    messages = [{"role": "user", "content": "Search the web for 'OpenAI' and summarize in one sentence."}]
    response = client.chat.completions.create(
        model="google/gemini-3.1-flash-lite",
        messages=messages,
        tools=ai_tools,
        temperature=0.2,
    )

    message = response.choices[0].message
    if not message.tool_calls:
        pytest.skip("Model did not call tools; cannot validate tool-call roundtrip")

    messages.append(
        {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        }
    )

    for tc in message.tool_calls:
        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        tool_result = ToolRegistry.execute_tool(f"mcp__{server_name}", {"mcp_tool_name": tc.function.name, "mcp_tool_args": args})
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(tool_result), "name": tc.function.name})

    second_response = client.chat.completions.create(model="google/gemini-3.1-flash-lite", messages=messages, temperature=0.2)
    final_content = second_response.choices[0].message.content or ""
    assert final_content.strip()
