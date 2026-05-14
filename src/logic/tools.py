import os
import json
import requests
from bs4 import BeautifulSoup
from src.logic.mcp_client import NativeMcpClient

class ToolRegistry:
    _native_mcp_client = NativeMcpClient()
    _mcp_config = None
    _active_mcp_servers = {}

    @classmethod
    def _load_mcp_config(cls):
        if cls._mcp_config is not None:
            return cls._mcp_config
            
        config_path = "config/mcp_default.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    all_servers = json.load(f).get("mcpServers", {})
                    # Only keep enabled servers
                    active_servers = {k: v for k, v in all_servers.items() if not v.get("disabled", False)}
                    cls._mcp_config = active_servers
                    return cls._mcp_config
            except Exception as e:
                print(f"Failed to read local MCP config: {e}")
                
        cls._mcp_config = {}
        return cls._mcp_config

    @classmethod
    def get_available_tools(cls) -> list[str]:
        tools = ["web_search", "fetch_url", "calculator", "get_current_time"]
        
        # Add MCP servers as tools prefix
        mcp_servers = cls._load_mcp_config()
        for server_name in mcp_servers.keys():
            tools.append(f"mcp__{server_name}")
            
        return tools

    @classmethod
    def execute_tool(cls, tool_name: str, args: dict) -> str:
        try:
            if tool_name == "web_search":
                return cls._web_search(args)
            elif tool_name == "fetch_url":
                return cls._fetch_url(args)
            elif tool_name == "calculator":
                return cls._calculator(args)
            elif tool_name == "get_current_time":
                return cls._get_current_time()
            elif tool_name.startswith("mcp__"):
                server_name = tool_name[5:]
                return cls._execute_mcp_tool(server_name, args)
            else:
                return f"Error: Tool '{tool_name}' not found."
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    @classmethod
    def get_mcp_server_tools(cls, server_name: str) -> list:
        config = cls._load_mcp_config().get(server_name)
        if not config:
            return []
            
        if server_name not in cls._active_mcp_servers:
            success = cls._native_mcp_client.start_server(server_name, config)
            if not success:
                return []
            cls._active_mcp_servers[server_name] = True
            
        return cls._native_mcp_client.get_tools(server_name)

    @classmethod
    def _execute_mcp_tool(cls, server_name: str, args: dict) -> str:
        try:
            config = cls._load_mcp_config().get(server_name)
            if not config:
                return f"Error: MCP server '{server_name}' configuration not found."
    
            # Ensure server is running natively
            if server_name not in cls._active_mcp_servers:
                success = cls._native_mcp_client.start_server(server_name, config)
                if not success:
                    return f"Error: Failed to start MCP server '{server_name}' natively."
                cls._active_mcp_servers[server_name] = True
                
            mcp_tool_name = args.get("mcp_tool_name")
            if not mcp_tool_name:
                return f"Error: MCP execution requires 'mcp_tool_name' parameter in the JSON body. Provided args: {args}"
                
            mcp_tool_args = args.get("mcp_tool_args", {})
            if isinstance(mcp_tool_args, str):
                try:
                    mcp_tool_args = json.loads(mcp_tool_args)
                except:
                    pass
                    
            import asyncio
            
            async def run_with_timeout():
                return await asyncio.to_thread(cls._native_mcp_client.execute_tool, server_name, mcp_tool_name, mcp_tool_args)
                
            try:
                # We might be in a thread where there is no running event loop.
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                    
                if loop and loop.is_running():
                    # If we are already in an event loop (e.g. FastAPI thread), we just do a blocking wait
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(cls._native_mcp_client.execute_tool, server_name, mcp_tool_name, mcp_tool_args)
                        return future.result(timeout=45.0)
                else:
                    # No loop running in this thread, create one and run it
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(asyncio.wait_for(run_with_timeout(), timeout=45.0))
                    finally:
                        new_loop.close()
            except Exception as te:
                return f"Error: Tool '{mcp_tool_name}' on server '{server_name}' timed out or crashed: {str(te)}"
        except Exception as e:
            return f"Error setting up MCP execution for '{server_name}': {str(e)}"

    @staticmethod
    def _web_search(args: dict) -> str:
        query = args.get("query", "")
        if not query:
            return "Error: Missing 'query' parameter."
        
        # Simple duckduckgo html search scraping as a fallback if no API key
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            results = []
            for a in soup.find_all('a', class_='result__snippet'):
                results.append(a.text)
                if len(results) >= 3:
                    break
            if not results:
                return "No results found."
            return "\n".join([f"- {r}" for r in results])
        except Exception as e:
            return f"Search failed: {str(e)}"

    @staticmethod
    def _fetch_url(args: dict) -> str:
        url = args.get("url", "")
        if not url:
            return "Error: Missing 'url' parameter."
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Extract basic text
            text = soup.get_text(separator=' ', strip=True)
            return text[:2000] + ("..." if len(text) > 2000 else "")
        except Exception as e:
            return f"Fetch failed: {str(e)}"

    @staticmethod
    def _calculator(args: dict) -> str:
        expr = args.get("expression", "")
        if not expr:
            return "Error: Missing 'expression' parameter."
        try:
            # Very basic safe eval for math
            allowed_names = {"__builtins__": None}
            result = eval(expr, allowed_names, {})
            return str(result)
        except Exception as e:
            return f"Calculation failed: {str(e)}"

    @staticmethod
    def _get_current_time() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
