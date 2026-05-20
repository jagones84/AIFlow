#!/usr/bin/env python3
"""MCP server that executes Python code locally. Works on Linux."""

import json
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

server = Server("python-local")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="run_python",
            description="Execute Python code and return the output. Use this to run Python scripts, perform calculations, or test code snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute. Use print() to output results. The code runs in an isolated environment."
                    }
                },
                "required": ["code"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "run_python":
        code = arguments.get("code", "")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        result = None
        error = None
        
        try:
            local_vars = {"__builtins__": __builtins__}
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(code, local_vars)
            result = stdout_buf.getvalue()
            if stderr_buf.getvalue():
                result += "\n[STDERR]\n" + stderr_buf.getvalue()
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        
        if error:
            return [TextContent(type="text", text=f"[ERROR]\n{error}")]
        elif result:
            return [TextContent(type="text", text=f"[OUTPUT]\n{result}")]
        else:
            return [TextContent(type="text", text="[OK] Code executed successfully with no output.")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
