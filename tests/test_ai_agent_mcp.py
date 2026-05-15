import os
import json
from dotenv import load_dotenv
from src.logic.tools import ToolRegistry
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

# Test with Brave Search MCP
tool_name = "mcp__Brave Search"
server_name = "Brave Search"

# Get the real schema from MCP
mcp_tools = ToolRegistry.get_mcp_server_tools(server_name)
safe_name = "brave_web_search"
tool_schema = next((t for t in mcp_tools if t["name"] == safe_name), None)

ai_tools = []
if tool_schema:
    ai_tools.append({
        "type": "function",
        "function": {
            "name": safe_name,
            "description": tool_schema.get("description", "Search web"),
            "parameters": tool_schema.get("inputSchema", {"type": "object", "properties": {"query": {"type": "string"}}})
        }
    })

messages = [
    {"role": "user", "content": "latest soccer italian match with result, search for it"}
]

print("1. Sending request to OpenRouter with tools:", [t["function"]["name"] for t in ai_tools])
response = client.chat.completions.create(
    model="x-ai/grok-4.1-fast",
    messages=messages,
    tools=ai_tools,
    temperature=0.7
)

message = response.choices[0].message
print("2. Received initial response:")
print(f"Content: {message.content}")
print(f"Tool calls: {message.tool_calls}")

if message.tool_calls:
    # Append the assistant message properly
    # Using a clean dict instead of model_dump to avoid OpenRouter issues with extra fields
    clean_msg = {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in message.tool_calls
        ]
    }
    messages.append(clean_msg)
    
    for tc in message.tool_calls:
        args = json.loads(tc.function.arguments)
        print(f"3. Executing tool {tc.function.name} with args {args}")
        
        mcp_args = {
            "mcp_tool_name": tc.function.name,
            "mcp_tool_args": args
        }
        res = ToolRegistry.execute_tool(tool_name, mcp_args)
        print(f"4. Tool result (first 100 chars): {str(res)[:100]}")
        
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": str(res),
            "name": tc.function.name
        })
        
    print("5. Sending second request to OpenRouter...")
    second_response = client.chat.completions.create(
        model="x-ai/grok-4.1-fast",
        messages=messages,
        temperature=0.7
    )
    print("6. Final Answer Raw Object:")
    print(second_response)
    print("Final Content:", second_response.choices[0].message.content)
else:
    print("No tools called.")
