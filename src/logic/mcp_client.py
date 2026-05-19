import os
import json
import subprocess
import threading
from typing import Dict, Any

class NativeMcpClient:
    """A minimal JSON-RPC over stdio MCP client to run servers natively in Python."""
    
    def __init__(self):
        self._processes = {}
        self._message_id = 1
        self._locks = {}

    def start_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        if server_name in self._processes:
            return True

        command = config.get("command")
        if not command:
            print(f"Error: No 'command' specified for native MCP server {server_name}")
            return False

        args = config.get("args", [])
        
        # Merge system env with specific tool env and global API keys
        env = os.environ.copy()
        
        # Inject standard API keys from our .env if they exist, so the MCP servers can pick them up
        if os.getenv("BRAVE_API_KEY"): env["BRAVE_API_KEY"] = os.getenv("BRAVE_API_KEY")
        if os.getenv("TAVILY_API_KEY"): env["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
        if os.getenv("HF_TOKEN"): env["HF_TOKEN"] = os.getenv("HF_TOKEN")
        if os.getenv("MAPBOX_API_KEY"): env["MAPBOX_API_KEY"] = os.getenv("MAPBOX_API_KEY")
        if os.getenv("YOUTUBE_API_KEY"): env["YOUTUBE_API_KEY"] = os.getenv("YOUTUBE_API_KEY")
        if os.getenv("GITHUB_TOKEN"): 
            env["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = os.getenv("GITHUB_TOKEN")
            
        custom_env = config.get("env", {})
        for k, v in custom_env.items():
            sv = "" if v is None else str(v)
            is_placeholder = (not sv) or sv.startswith("YOUR_") or sv.startswith("your_") or sv.startswith("INSERISCI")
            if is_placeholder and env.get(k):
                continue
            env[k] = sv
            
        cwd = config.get("cwd") or config.get("workingDirectory")

        try:
            # On Windows, we might need shell=True for some commands like 'npm' or 'npx'
            shell = os.name == 'nt' and (command.endswith('.cmd') or command.endswith('.bat') or command in ['npm', 'npx'])
            
            process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=cwd,
                shell=shell,
                text=True,
                bufsize=1 # Line buffered
            )
            
            self._processes[server_name] = process
            self._locks[server_name] = threading.Lock()
            
            # Send MCP Initialize Request
            init_req = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "aiflow-python", "version": "1.0.0"}
                }
            }
            res = self._send_request(server_name, init_req)
            
            if "result" in res:
                # Send initialized notification
                notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                self._send_raw(server_name, notif)
                return True
            else:
                print(f"MCP Initialize failed for {server_name}: {res}")
                return False
                
        except Exception as e:
            print(f"Error starting native MCP server {server_name}: {e}")
            return False

    def get_tools(self, server_name: str) -> list:
        if server_name not in self._processes:
            return []
            
        req = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list"
        }
        
        res = self._send_request(server_name, req)
        if "result" in res and "tools" in res["result"]:
            return res["result"]["tools"]
        return []

    def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> str:
        if server_name not in self._processes:
            return f"Error: MCP Server '{server_name}' is not running."
            
        req = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        res = self._send_request(server_name, req)
        
        if "result" in res and "content" in res["result"]:
            content = res["result"]["content"]
            return self._parse_mcp_content(content)
        elif "error" in res:
            return f"MCP Tool Error: {res['error']}"
        else:
            return f"MCP Tool Error: {json.dumps(res)}"

    @staticmethod
    def _parse_mcp_content(content) -> str:
        if isinstance(content, list) and len(content) > 0:
            item = content[0]
            if isinstance(item, dict):
                text = item.get("text")
                if text is not None:
                    return str(text)
            return json.dumps(content)
        return str(content)

    def _get_next_id(self):
        current = self._message_id
        self._message_id += 1
        return current

    def _send_raw(self, server_name: str, payload: dict):
        proc = self._processes.get(server_name)
        if not proc or proc.poll() is not None:
            raise Exception(f"Process {server_name} is dead.")
            
        msg = json.dumps(payload) + "\n"
        proc.stdin.write(msg)
        proc.stdin.flush()

    def _send_request(self, server_name: str, payload: dict) -> dict:
        lock = self._locks.get(server_name)
        if not lock:
            return {"error": "Server lock not found."}
            
        with lock:
            self._send_raw(server_name, payload)
            
            proc = self._processes.get(server_name)
            expected_id = payload.get("id")
            
            # Read until we get our response
            while True:
                line = proc.stdout.readline()
                if not line:
                    return {"error": "Process stdout closed unexpectedly."}
                    
                try:
                    data = json.loads(line.strip())
                    # Ignore other notifications/logs that might be interleaved
                    if "id" in data and data["id"] == expected_id:
                        return data
                except json.JSONDecodeError:
                    # Some MCP servers log plain text to stdout despite the spec, ignore it
                    continue
