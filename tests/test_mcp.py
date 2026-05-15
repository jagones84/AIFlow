from src.logic.tools import ToolRegistry
from dotenv import load_dotenv
import os

load_dotenv()

print("Testing Fetch...")
res = ToolRegistry.execute_tool("mcp__Fetch", {
    "mcp_tool_name": "fetch",
    "mcp_tool_args": {"url": "https://example.com"}
})
print("Result:", res)
