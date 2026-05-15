import json
import asyncio
from src.logic.tools import ToolRegistry

def test_all_active_tools():
    servers = ToolRegistry._load_mcp_config()
    
    print(f"Found {len(servers)} active MCP servers: {list(servers.keys())}")
    
    for server_name in servers:
        print(f"\n==========================================")
        print(f"Testing server: {server_name}")
        try:
            tools = ToolRegistry.get_mcp_server_tools(server_name)
            if not tools:
                print(f"  [WARN] No tools found for {server_name} or failed to connect.")
                continue
            print(f"  [OK] Successfully fetched {len(tools)} tools.")
            for t in tools:
                print(f"    - {t.get('name')}: {t.get('description', '')[:50]}...")
        except Exception as e:
            print(f"  [ERROR] Failed to fetch tools for {server_name}: {e}")

if __name__ == "__main__":
    test_all_active_tools()
