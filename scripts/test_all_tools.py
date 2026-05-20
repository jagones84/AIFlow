#!/usr/bin/env python3
"""
Test script for all MCP tools using the app functions directly.
Tests each tool's execution path as used by the AI Agent.
"""

import os
import sys
import json
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logic.tools import ToolRegistry
from src.logic.mcp_client import NativeMcpClient

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ToolTester:
    def __init__(self):
        self.results = []
        self.native_client = NativeMcpClient()
        
    def log(self, status, tool, message=""):
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "ℹ️"
        result = f"{emoji} [{status}] {tool}: {message}"
        self.results.append((status, tool, message))
        print(result)
        
    def test_basic_tools(self):
        print("\n" + "="*60)
        print("TESTING BASIC TOOLS")
        print("="*60)
        
        # Test calculator
        try:
            result = ToolRegistry.execute_tool("calculator", {"expression": "2 + 2"})
            if "4" in result:
                self.log("PASS", "calculator", f"Result: {result[:100]}")
            else:
                self.log("FAIL", "calculator", f"Unexpected result: {result[:100]}")
        except Exception as e:
            self.log("FAIL", "calculator", str(e))
            
        # Test get_current_time
        try:
            result = ToolRegistry.execute_tool("get_current_time", {})
            if "time" in result.lower() or ":" in result:
                self.log("PASS", "get_current_time", f"Result: {result[:100]}")
            else:
                self.log("FAIL", "get_current_time", f"Unexpected result: {result[:100]}")
        except Exception as e:
            self.log("FAIL", "get_current_time", str(e))
            
        # Test fetch_url
        try:
            result = ToolRegistry.execute_tool("fetch_url", {"url": "https://httpbin.org/html"})
            if len(result) > 50:
                self.log("PASS", "fetch_url", f"Fetched {len(result)} chars")
            else:
                self.log("FAIL", "fetch_url", f"Too short: {result[:100]}")
        except Exception as e:
            self.log("FAIL", "fetch_url", str(e))
            
    def test_mcp_servers(self):
        print("\n" + "="*60)
        print("TESTING MCP SERVERS")
        print("="*60)
        
        # Load MCP config
        mcp_config = ToolRegistry._load_mcp_config()
        print(f"\nFound {len(mcp_config)} MCP servers in config:")
        
        for server_name, config in mcp_config.items():
            print(f"\n--- Testing MCP Server: {server_name} ---")
            print(f"  Command: {config.get('command', 'N/A')}")
            print(f"  Args: {config.get('args', [])}")
            
            # Test starting the server
            try:
                success = self.native_client.start_server(server_name, config)
                if success:
                    self.log("PASS", f"MCP:{server_name}", "Server started successfully")
                else:
                    self.log("FAIL", f"MCP:{server_name}", "Failed to start server")
                    continue
            except Exception as e:
                self.log("FAIL", f"MCP:{server_name}", f"Exception starting: {str(e)}")
                continue
                
            # Test getting tools from server
            try:
                tools = self.native_client.get_tools(server_name)
                self.log("PASS", f"MCP:{server_name}", f"Found {len(tools)} tools")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"    - {tool.get('name', 'unknown')}: {tool.get('description', '')[:60]}")
                if len(tools) > 5:
                    print(f"    ... and {len(tools) - 5} more")
            except Exception as e:
                self.log("FAIL", f"MCP:{server_name}", f"Exception getting tools: {str(e)}")
                continue
                
            # Test executing each tool
            for tool in tools:
                tool_name = tool.get('name', '')
                if not tool_name:
                    continue
                    
                # Prepare test arguments based on tool type
                test_args = self._get_test_args_for_tool(tool_name)
                
                try:
                    result = self.native_client.execute_tool(server_name, tool_name, test_args)
                    if result and len(result) > 0 and "error" not in result.lower()[:100]:
                        self.log("PASS", f"MCP:{server_name}.{tool_name}", f"Result: {result[:80]}...")
                    else:
                        self.log("FAIL", f"MCP:{server_name}.{tool_name}", f"Error or empty: {result[:100]}")
                except Exception as e:
                    self.log("FAIL", f"MCP:{server_name}.{tool_name}", str(e))
                    
    def _get_test_args_for_tool(self, tool_name: str) -> dict:
        """Return appropriate test arguments based on tool name."""
        test_args = {}
        
        # Brave Search
        if "search" in tool_name.lower() or "brave" in tool_name.lower():
            test_args = {"query": "latest soccer match Italy Serie A"}
        elif "fetch" in tool_name.lower() or "url" in tool_name.lower():
            test_args = {"url": "https://httpbin.org/json"}
        elif "time" in tool_name.lower() or "date" in tool_name.lower():
            test_args = {}
        elif "weather" in tool_name.lower():
            test_args = {"location": "Rome, Italy"}
        elif "news" in tool_name.lower():
            test_args = {"query": "technology news"}
        elif "calculator" in tool_name.lower() or "math" in tool_name.lower():
            test_args = {"expression": "10 * 5 + 3"}
        elif "code" in tool_name.lower() or "execute" in tool_name.lower():
            test_args = {"code": "print('Hello from test')"}
        elif "file" in tool_name.lower() or "read" in tool_name.lower():
            test_args = {"path": "/tmp"}
        elif "git" in tool_name.lower() or "github" in tool_name.lower():
            test_args = {"query": "openai"}
        elif "multi" in tool_name.lower() or "fetch" in tool_name.lower():
            test_args = {"urls": ["https://httpbin.org/get", "https://httpbin.org/ip"]}
        elif "memory" in tool_name.lower():
            if "create_entities" in tool_name:
                test_args = {"entities": [{"entityType": "test", "name": "TestEntity", "observations": ["test observation"]}]}
            elif "create_relations" in tool_name:
                test_args = {"relations": [{"from": "Test1", "to": "Test2", "relationType": "related_to"}]}
            elif "add_observations" in tool_name:
                test_args = {"observations": [{"entityName": "Test", "contents": ["test content"]}]}
            elif "delete" in tool_name:
                test_args = {"entityNames": ["Test"]}
            elif "open" in tool_name:
                test_args = {"names": ["Test"]}
            elif "search" in tool_name:
                test_args = {"query": "test"}
            else:
                test_args = {}
        else:
            # Generic test
            test_args = {"input": "test"}
            
        return test_args
        
    def print_summary(self):
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        passed = sum(1 for s, _, _ in self.results if s == "PASS")
        failed = sum(1 for s, _, _ in self.results if s == "FAIL")
        total = len(self.results)
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for status, tool, msg in self.results:
                if status == "FAIL":
                    print(f"  - {tool}: {msg}")
                    
        return failed == 0


def main():
    tester = ToolTester()
    
    # Test basic tools
    tester.test_basic_tools()
    
    # Test MCP servers
    tester.test_mcp_servers()
    
    # Print summary
    success = tester.print_summary()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
