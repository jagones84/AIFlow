from src.logic.tools import ToolRegistry

print("Testing Multi-Fetch tools...")
tools = ToolRegistry.get_mcp_server_tools("Multi-Fetch")
print("Available tools:", [t["name"] for t in tools])

print("\nTesting Brave Search execution...")
res = ToolRegistry.execute_tool("mcp__Brave Search", {
    "mcp_tool_name": "brave_web_search",
    "mcp_tool_args": {"query": "latest soccer match italy serie A"}
})
print("Brave Search Result length:", len(str(res)))
print("Preview:", str(res)[:200])
