import os
import json
import requests
from typing import Dict, Any

class PcBridgeClient:
    """Client to communicate with the PC Bridge server (mcp-bridge) which runs the MCP servers"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()

    def is_bridge_reachable(self) -> bool:
        try:
            res = self.session.get(f"{self.base_url}/ping", timeout=5)
            return res.ok
        except:
            return False

    def start_remote_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        url = f"{self.base_url}/mcp/start"
        payload = {
            "server_name": server_name,
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "env": config.get("env", {})
        }
        try:
            res = self.session.post(url, json=payload, timeout=10)
            return res.ok
        except Exception as e:
            print(f"Error starting remote server {server_name}: {e}")
            return False

    def stop_remote_server(self, server_name: str) -> bool:
        url = f"{self.base_url}/mcp/stop"
        payload = {"server_name": server_name}
        try:
            res = self.session.post(url, json=payload, timeout=5)
            return res.ok
        except:
            return False

    def send_rpc_request(self, server_name: str, rpc_request: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/mcp/rpc"
        payload = {
            "server_name": server_name,
            "request": rpc_request
        }
        try:
            res = self.session.post(url, json=payload, timeout=180) # MCP tools can take a while
            if res.ok:
                data = res.json()
                if "response" in data:
                    return {"success": True, "response": data["response"]}
                elif "error" in data:
                    return {"success": False, "error": data["error"]}
                return {"success": False, "error": "Invalid response format"}
            else:
                try:
                    err = res.json().get("error", f"HTTP {res.status_code}")
                except:
                    err = f"HTTP {res.status_code}"
                return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> str:
        """Helper to specifically execute an MCP tool via RPC"""
        rpc_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        res = self.send_rpc_request(server_name, rpc_req)
        if res["success"]:
            # Parse MCP tool result format
            response_data = res["response"]
            if "result" in response_data and "content" in response_data["result"]:
                content = response_data["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    return str(content[0].get("text", content))
                return str(content)
            return json.dumps(response_data)
        else:
            return f"MCP Tool Error: {res.get('error', 'Unknown')}"
